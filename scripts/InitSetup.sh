#!/bin/bash -xeu

# 前提：gitとbash,sudoが利用できる環境が条件
#       zsh, cshなどは想定外

readonly RC_NORMAL=0
readonly RC_ERROR=1

PYENV_GIT_URL="https://github.com/pyenv/pyenv.git"
CLONE_ROOT_PATH="/opt"
PYENV_ROOT_PATH="${CLONE_ROOT_PATH}/pyenv"
BASH_PROFILE_FILE="${HOME}/.bash_profile"
INSTALL_PYTHON_VERSION="3.9.1"

function CheckUseSudoCommand() {
  set +e
  sudo -l >> /dev/null 2>&1
  isPrivilegedRoot=$?
  
  if [[ "${isPrivilegedRoot}" != ${RC_NORMAL} ]]
  then
    echo "このスクリプトは利用できません。特権権限に昇格できるユーザで実行してください。"
    exit ${RC_ERROR}
  fi
  set -e
  
  return ${RC_NORMAL}
}

function SetupPyenv() {
  if [[ -d "${PYENV_ROOT_PATH}" ]]
  then
    return ${RC_NORMAL}
  fi
  
  pushd ${CLONE_ROOT_PATH}
  sudo git clone ${PYENV_GIT_URL}
  sudo chown -R $(whoami): ${PYENV_ROOT_PATH}
  popd
  
  return ${RC_NORMAL}
}

function SetupPyenvConfiguration() {
  if [[ "$(egrep '^which pyenv' ${BASH_PROFILE_FILE})" == "" ]]
  then
    echo 'which pyenv >> /dev/null 2>&1 && eval "$(pyenv init -)"' >> ${BASH_PROFILE_FILE}
  fi
  
  source ${BASH_PROFILE_FILE}
  
  return ${RC_NORMAL}
}

# 事前実行条件調査
CheckUseSudoCommand

# 環境のセットアップ
SetupPyenv
# SetupPyenvConfiguration

# 構築調査
which pyenv

yes Y | pipenv --python ${INSTALL_PYTHON_VERSION}

curl -kL https://bootstrap.pypa.io/get-pip.py | python
pipenv sync

exit ${RC_NORMAL}
