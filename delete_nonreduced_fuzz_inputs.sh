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

export FUZZ_CORPORA_DIR="fuzz_corpora"

set -e

echo "Installing Bitcoin Core build deps"
export DEBIAN_FRONTEND=noninteractive
apt update
apt install -y \
  git \
  build-essential pkg-config bsdmainutils python3 cmake \
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
  mv ./"${FUZZ_CORPORA_DIR}" ../all_inputs
  git config user.name "delete_nonreduced_inputs script"
  git config user.email "noreply@noreply.noreply"
  git commit -a -m "Delete fuzz inputs"
)

git clone --depth=1 https://github.com/bitcoin/bitcoin.git
(
  cd bitcoin

  echo "Adding reduced seeds with afl-cmin"

  rm -rf build_fuzz/
  export LDFLAGS="-fuse-ld=lld"
  cmake -B build_fuzz \
    -DCMAKE_C_COMPILER=afl-clang-fast -DCMAKE_CXX_COMPILER=afl-clang-fast++ \
    -DBUILD_FOR_FUZZING=ON
  cmake --build build_fuzz -j$(nproc)

  WRITE_ALL_FUZZ_TARGETS_AND_ABORT="/tmp/a" "./build_fuzz/src/test/fuzz/fuzz" || true
  readarray FUZZ_TARGETS < "/tmp/a"
  for fuzz_target in ${FUZZ_TARGETS[@]}; do
    if [ -d "../all_inputs/$fuzz_target" ]; then
      mkdir --parents ../qa-assets/"${FUZZ_CORPORA_DIR}"/$fuzz_target
      # Allow timeouts and crashes with "-A", "-T all" to use all available cores
      FUZZ=$fuzz_target afl-cmin -T all -A -i ../all_inputs/$fuzz_target -o ../qa-assets/"${FUZZ_CORPORA_DIR}"/$fuzz_target -- ./build_fuzz/src/test/fuzz/fuzz
    else
      echo "No input corpus for $fuzz_target (ignoring)"
    fi
  done

  (
    cd ../qa-assets
    git add "${FUZZ_CORPORA_DIR}"
    git commit -m "Reduced inputs for afl-cmin"
  )

  for sanitizer in {"fuzzer","fuzzer,address,undefined,integer"}; do
    echo "Adding reduced seeds for sanitizer=${sanitizer}"

    rm -rf build_fuzz/
    cmake -B build_fuzz \
      -DCMAKE_C_COMPILER=clang-$LLVM_VERSION -DCMAKE_CXX_COMPILER=clang++-$LLVM_VERSION \
      -DBUILD_FOR_FUZZING=ON -DSANITIZERS="$sanitizer"
    cmake --build build_fuzz -j$(nproc)

    ( cd build_fuzz; ./test/fuzz/test_runner.py -l DEBUG --par=$(nproc) --m_dir=../../all_inputs ../../qa-assets/"${FUZZ_CORPORA_DIR}" )

    (
      cd ../qa-assets
      git add "${FUZZ_CORPORA_DIR}"
      git commit -m "Reduced inputs for ${sanitizer}"
    )
  done
)
