# Over time the fuzz engine will reduce inputs (produce a smaller input that
# yields the same coverage statistics). With a growing set of inputs, it could
# be useful to occasionally delete the "old" non-reduced inputs.
#
# This script tries to do so in a way that is as deterministic as possible.
#
# The script should be run on an x86_64 virtual machine with only a minimal
# vanilla Ubuntu Noble 24.04 installed.  Ideally, the script was run on
# different architectures or even different OS versions, which come with
# different library packages, but this is left as a future improvement.

export FUZZ_INPUTS_DIR="fuzz_seed_corpus"

set -e

echo "Installing Bitcoin Core build deps"
export DEBIAN_FRONTEND=noninteractive
apt update
apt install -y \
  git \
  build-essential libtool autotools-dev automake pkg-config bsdmainutils python3 \
  libsqlite3-dev libevent-dev libboost-dev \
  lsb-release wget software-properties-common gnupg

export LLVM_VERSION=18
wget https://apt.llvm.org/llvm.sh && chmod +x ./llvm.sh
./llvm.sh $LLVM_VERSION all
ln -s $(which llvm-symbolizer-$LLVM_VERSION) /usr/bin/llvm-symbolizer

git clone --branch stable https://github.com/AFLplusplus/AFLplusplus
make -C AFLplusplus LLVM_CONFIG=llvm-config-$LLVM_VERSION PERFORMANCE=1 install -j$(nproc)

git clone --depth=1 https://github.com/bitcoin-core/qa-assets.git
(
  cd qa-assets
  mv ./"${FUZZ_INPUTS_DIR}" ../all_inputs
  git config user.name "delete_nonreduced_inputs script"
  git config user.email "noreply@noreply.noreply"
  git commit -a -m "Delete fuzz inputs"
)

git clone --depth=1 https://github.com/bitcoin/bitcoin.git
(
  cd bitcoin

  ./autogen.sh

  echo "Adding reduced seeds with afl-cmin"

  ./configure LDFLAGS="-fuse-ld=lld" CC=afl-clang-fast CXX=afl-clang-fast++ --enable-fuzz
  make clean
  make -j $(nproc)

  WRITE_ALL_FUZZ_TARGETS_AND_ABORT="/tmp/a" "./src/test/fuzz/fuzz" || true
  readarray FUZZ_TARGETS < "/tmp/a"
  for fuzz_target in ${FUZZ_TARGETS[@]}; do
    if [ -d "../all_inputs/$fuzz_target" ]; then
      mkdir --parents ../qa-assets/"${FUZZ_INPUTS_DIR}"/$fuzz_target
      # Allow timeouts and crashes with "-A", "-T all" to use all available cores
      FUZZ=$fuzz_target afl-cmin -T all -A -i ../all_inputs/$fuzz_target -o ../qa-assets/"${FUZZ_INPUTS_DIR}"/$fuzz_target -- ./src/test/fuzz/fuzz
    else
      echo "No input corpus for $fuzz_target (ignoring)"
    fi
  done

  (
    cd ../qa-assets
    git add "${FUZZ_INPUTS_DIR}"
    git commit -m "Reduced inputs for afl-cmin"
  )

  for sanitizer in {"fuzzer","fuzzer,address,undefined,integer"}; do
    echo "Adding reduced seeds for sanitizer=${sanitizer}"

    ./configure LDFLAGS="-fuse-ld=lld" CC=clang-$LLVM_VERSION CXX=clang++-$LLVM_VERSION --enable-fuzz --with-sanitizers="${sanitizer}"
    make clean
    make -j $(nproc)

    ./test/fuzz/test_runner.py -l DEBUG --par=$(nproc) --m_dir=../all_inputs ../qa-assets/"${FUZZ_INPUTS_DIR}"

    (
      cd ../qa-assets
      git add "${FUZZ_INPUTS_DIR}"
      git commit -m "Reduced inputs for ${sanitizer}"
    )
  done
)
