#!/bin/bash

###
### Download the virtualenv install assistant:
### curl https://raw.github.com/ibest/ARC/develop/contrib/virt-installer.sh > virt-installer.sh
###
### Run the installer
### sh virt-installer.sh <branch>
###
### Example (For the stable version)
### sh virt-installer.sh
###
### Example (For the development branch)
### sh virt-installer.sh develop
###
### Notes:
### When installing on OSX you may see alot of warnings when compiling the numpy
### libraries.  You can safely ignore them.
###

set -e

BRANCH="stable"
if [ $# -eq 1 ] ; then
  BRANCH=$1
fi
BLATZIPBALL="http://users.soe.ucsc.edu/~kent/src/blatSrc${BLATVER}.zip"
BLATPATCH="https://raw.github.com/ibest/ARC/develop/contrib/blat_fastq_support.patch"
BOWTIE2ZIPBALL="http://sourceforge.net/projects/bowtie-bio/files/latest/download?source=files"

MACHTYPE=$(uname -s)

if [ "$MACHTYPE" == "Darwin" ] ; then
  SPADESTARBALL="http://spades.bioinf.spbau.ru/release2.5.0/SPAdes-2.5.0-Darwin.tar.gz"
else
  SPADESTARBALL="http://spades.bioinf.spbau.ru/release2.5.0/SPAdes-2.5.0-Linux.tar.gz"
fi

# Is pip installed
command -v pip > /dev/null 2>&1 || { 
  echo >&2 "Please install pip before continuing.";
  exit 1
}

# Is virtualenv installed
command -v virtualenv > /dev/null 2>&1 || { 
  echo >&2 "Please install virtualenv before continuing.";
  exit 1
}

# Is git installed
command -v git > /dev/null 2>&1 || { 
  echo >&2 "Please install git before continuing.";
  exit 1
}

# Is git installed
command -v curl > /dev/null 2>&1 || { 
  echo >&2 "Please install curl before continuing.";
  exit 1
}

# Setup a new virtualenv
virtualenv arc
source arc/bin/activate

echo "Installing required python modules (numpy)"
python -c "import numpy" > /dev/null 2>&1 || {
  pip install numpy
}

echo "Installing required python modules (Biopython)"
python -c "import Bio" > /dev/null 2>&1 || {
  pip install Biopython
}

echo "Cloning arc from the $BRANCH branch."
pushd arc
mkdir share
mkdir src

pushd src # arc/src
if [ ! -f ./ARC/README.md ] ; then
  git clone https://github.com/ibest/ARC.git
else
  echo "ARC has already been cloned in src."
fi

pushd ARC # arc/src/ARC
CURR_BRANCH=$(git branch | sed -n '/\* /s///p')
if [ "$CURR_BRANCH" != "$BRANCH" ] ; then
  echo "Branch differs.  Checking out the requested branch."
  git checkout $BRANCH
  # Reinstall since we changed branches
  echo "Reinstalling."
  python setup.py install
else
  command -v ARC > /dev/null 2>&1 || {
    echo "Installing."
    python setup.py install
  }
fi
popd # arc/src

export MACHTYPE
# Grab the path to our virtualenv bin folder
export BINDIR=$(echo $PATH | cut -d':' -f1)

echo "Installing Blat"
command -v blat > /dev/null 2>&1 || {
  if [ ! -f src/blat.zip ] ; then
    curl -L $BLATZIPBALL > blat.zip
    unzip blat.zip
    # cp -f $BLATPATCH blatSrc/.
    pushd blatSrc # arc/src/blatSrc
    echo "Downloading the blat fastq patch..."
    curl $BLATPATCH > blat_fastq_support.patch
    patch -p2 < blat_fastq_support.patch
    make
    popd # arc/src
  fi
}

echo "Installing Bowtie2"
command -v bowtie2 > /dev/null 2>&1 || {
  if [ ! -f src/bowtie2.zip ] ; then
    curl -L $BOWTIE2ZIPBALL > bowtie2.zip
    unzip bowtie2.zip
    pushd bowtie2-* # arc/src/bowtie2-*
    make
    install -c bowtie2 $BINDIR
    for file in bowtie2-*[a-z] ; do 
      install -c $file $BINDIR
    done
    popd # arc/src
  fi
}

echo "Installing Spades"
command -v spades > /dev/null 2>&1 || {
  if [ ! -f src/spades.zip ] ; then
    curl -L $SPADESTARBALL > SPAdes.tar.gz
    tar zxvf SPAdes.tar.gz
    pushd SPAdes-* # arc/src/SPAdes-*
    install -c bin/bwa-spades $BINDIR
    install -c bin/spades $BINDIR
    install -c bin/hammer $BINDIR
    install -c bin/spades.py $BINDIR
    install -c bin/spades_init.py $BINDIR
    mv share/spades ../../share
    popd # arc/src
  fi
}

popd # arc

if [ ! -d data ] ; then
  cp -rf src/ARC/test_data data
fi

echo "The installation is complete.  You will need to download and install"
echo "newbler from Roche before running ARC if you are using newbler as your"
echo "assembler."
