#!/bin/bash

# This script will do code related release preparation stuff for Bitcoin Core as specified in
# the release-process.md file.
# This should be run from the folder containing the Source tree
# The following actions will be done:
#  1. Set the version numbers as specified in the arguments
#  2. Update src/chainparams.cpp nMinimumChainWork and defaultAssumeValid with information from the getblockchaininfo rpc.
#  3. Update Hard coded seeds
#  4. Set BLOCK_CHAIN_SIZE
#  5. Update translations
#  6. Generate updated manpages
# Note: Step 2 assumes that an up-to-date Bitcoin Core is running and has been built in the
# directory which this script is being run.

# Variables
VERSION=
BLOCK_CHAIN_SIZE=
DATADIR=""
verBump=true
chainparamsUpdate=true
seedUpdate=true
blockchainsizeBump=true
translationsUpdate=true
genManpages=true

# Help Message
read -d '' usage <<- EOF
Usage: $scriptName version block_chain_size

Run this script from the Bitcoin Core Source root directory. This requires a current version of Bitcoin Core
to be running at the time that this script is run.

Arguments:
version		    Version number to set following the MAJOR.MINOR.REVISION format. Only required if
                    a version bump will be done. e.g. 29.0
block_chain_size    The size of the blockchain for the intro display. Should contain a little bit of 
                    overhead. Only required if BLOCK_CHAIN_SIZE will be updated. e.g. 120

Options:
--datadir <path>    The path to the data directory of the running Bitcoin Core node. Note that this is 
                    different from Bitcoin Core's -datadir option syntax. There is no equals, simply a space
                    followed by the path

--skip [v|c|s|b|t|m]   Skip the specified steps. v=version bump; c=update nMinimumChainwork and defaultAssumeValid
                       s=hard coded seed update; b=blockchain size bump; t=translations update; m=generate manpages.
                       The steps will be done in the order listed above.

EOF

# Get options and arguments
while :; do
    case $1 in
        # datadir
        --datadir)
	    if [ -n "$2" ]
	    then
		DATADIR="-datadir=$2"
		shift
	    else
		echo 'Error: "--datadir" requires an argument'
		exit 1
	    fi
	    ;;
        # skips
        --skip)
	    if [ -n "$2" ]
	    then
		if [[ "$2" = *"v"* ]]
		then
		    verBump=false
		fi
		if [[ "$2" = *"c"* ]]
		then
		    chainparamsUpdate=false
		fi
        if [[ "$2" = *"s"* ]]
		then
            seedUpdate=false
		fi
		if [[ "$2" = *"b"* ]]
		then
            blockchainsizeBump=false
		fi
		if [[ "$2" = *"t"* ]]
		then
            translationsUpdate=false
		fi
		if [[ "$2" = *"m"* ]]
		then
            genManpages=false
		fi
		shift
	    else
		echo 'Error: "--skip" requires an argument'
		exit 1
	    fi
	    ;;
	*)               # Default case: If no more options then break out of the loop.
        break
    esac
    shift
done

if [[ $verBump = true ]]
then
    # Bump Version numbers
    # Get version
    if [[ -n "$1" ]]
    then
        VERSION=$1
        shift
    fi

    # Check that a version is specified
    if [[ $VERSION == "" ]]
    then
        echo "$scriptName: Missing version."
        echo "Try $scriptName --help for more information"
        exit 1
    fi

    echo "Setting Version number"
    major=$(echo $VERSION | cut -d. -f1)
    minor=$(echo $VERSION | cut -d. -f2)
    rev=$(echo $VERSION | cut -d. -f3)

    # configure.ac
    sed -i "/define(_CLIENT_VERSION_MAJOR, /c\define(_CLIENT_VERSION_MAJOR, $major)" ./configure.ac
    sed -i "/define(_CLIENT_VERSION_MINOR, /c\define(_CLIENT_VERSION_MINOR, $minor)" ./configure.ac
    sed -i "/define(_CLIENT_VERSION_REVISION, /c\define(_CLIENT_VERSION_REVISION, $rev)" ./configure.ac
    sed -i "/define(_CLIENT_VERSION_IS_RELEASE, /c\define(_CLIENT_VERSION_IS_RELEASE, true)" ./configure.ac

    # src/clientversion.h
    sed -i "/#define CLIENT_VERSION_MAJOR /c\#define CLIENT_VERSION_MAJOR $major" ./src/clientversion.h
    sed -i "/#define CLIENT_VERSION_MINOR /c\#define CLIENT_VERSION_MINOR $minor" ./src/clientversion.h
    sed -i "/#define CLIENT_VERSION_REVISION /c\#define CLIENT_VERSION_REVISION $rev" ./src/clientversion.h
    sed -i "/#define CLIENT_VERSION_IS_RELEASE /c\#define CLIENT_VERSION_IS_RELEASE true" ./src/clientversion.h

    # docs
    sed -i "/PROJECT_NUMBER         = /c\PROJECT_NUMBER         = $VERSION" ./doc/Doxyfile
    sed -i "1s/.*/Bitcoin Core $VERSION/" ./doc/README.md
    sed -i "1s/.*/Bitcoin Core $VERSION/" ./doc/README_windows.txt

    # gitian descriptors
    sed -i "2s/.*/name: \"bitcoin-win-$major.$minor\"/" ./contrib/gitian-descriptors/gitian-win.yml
    sed -i "2s/.*/name: \"bitcoin-linux-$major.$minor\"/" ./contrib/gitian-descriptors/gitian-linux.yml
    sed -i "2s/.*/name: \"bitcoin-osx-$major.$minor\"/" ./contrib/gitian-descriptors/gitian-osx.yml
fi

if [[ $chainparamsUpdate = true ]]
then
    # Update nMinimumChainWork and defaultAssumeValid
    echo "Updating nMinimumChainWork and defaultAssumeValid"
    blockchaininfo=`src/bitcoin-cli ${DATADIR} getblockchaininfo`
    chainwork=`echo "$blockchaininfo" | jq -r '.chainwork'`
    bestblockhash=`echo "$blockchaininfo" | jq -r '.bestblockhash'`
    sed -i "0,/        consensus.nMinimumChainWork = uint256S(.*/s//        consensus.nMinimumChainWork = uint256S(\"0x$chainwork\");/" ./src/chainparams.cpp
    sed -i "0,/        consensus.defaultAssumeValid = uint256S(.*/s//        consensus.defaultAssumeValid = uint256S(\"0x$bestblockhash\");/" ./src/chainparams.cpp
fi

if [[ $seedUpdate = true ]]
then
    # Update Seeds
    echo "Updating hard coded seeds"
    pushd ./contrib/seeds
    curl -s http://bitcoin.sipa.be/seeds.txt > seeds_main.txt
    python makeseeds.py < seeds_main.txt > nodes_main.txt
    python generate-seeds.py . > ../../src/chainparamsseeds.h
popd
fi

if [[ $blockchainsizeBump = true ]]
then
    # Set blockchain size
    # Get block_chain_size
    if [[ -n "$1" ]]
    then
        BLOCK_CHAIN_SIZE=$1
        shift
    fi

    # Check that a block_chain_size is specified
    if [[ $BLOCK_CHAIN_SIZE == "" ]]
    then
        echo "$scriptName: Missing block_chain_size."
        echo "Try $scriptName --help for more information"
        exit 1
    fi
    echo "Setting BLOCK_CHAIN_SIZE"
    sed -i "/static const uint64_t BLOCK_CHAIN_SIZE = /c\static const uint64_t BLOCK_CHAIN_SIZE = $BLOCK_CHAIN_SIZE;" ./src/qt/intro.cpp
fi

if [[ $translationsUpdate = true ]]
then
    # Update translations
    echo "Updating translations"
    python contrib/devtools/update-translations.py
    ls src/qt/locale/*ts|xargs -n1 basename|sed 's/\(bitcoin_\(.*\)\).ts/<file alias="\2">locale\/\1.qm<\/file>/'
    ls src/qt/locale/*ts|xargs -n1 basename|sed 's/\(bitcoin_\(.*\)\).ts/ qt\/locale\/\1.ts \\/'
fi

if [[ $genManpages = true ]]
then
    # Generate manpages
    echo "Generating manpages"
    bash ./contrib/devtools/gen-manpages.sh
fi

# Complete
echo "Release preparation complete. Please use git to commit these changes"
