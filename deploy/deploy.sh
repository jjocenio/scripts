#!/bin/bash
# ---------------------------------------------------------------------------
# deploy.sh - Deploy spring boot app into coreos with docker

# Copyright 2015, jarbas,,, <jarbas@S46CB>
  
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License at <http://www.gnu.org/licenses/> for
# more details.

# Usage: deploy.sh [-h|--help] [-e env] [-r release]

# Revision history:
# 2015-11-02 Created by new_script.sh ver. 3.3
# ---------------------------------------------------------------------------

PROGNAME=${0##*/}
VERSION="0.1"

clean_up() { # Perform pre-exit housekeeping
  cd ${project_dir}
  rm -rf .deploy_*
  return
}

error_exit() {
  echo -e "${PROGNAME}: ${1:-"Unknown Error"}" >&2
  clean_up
  exit 1
}

graceful_exit() {
  clean_up
  exit
}

signal_exit() { # Handle trapped signals
  case $1 in
    INT)
      error_exit "Program interrupted by user" ;;
    TERM)
      echo -e "\n$PROGNAME: Program terminated" >&2
      graceful_exit ;;
    *)
      error_exit "$PROGNAME: Terminating on unknown signal" ;;
  esac
}

usage() {
  echo -e "Usage: $PROGNAME [-h|--help] [-e env] [-r release]"
}

help_message() {
  cat <<- _EOF_
  $PROGNAME ver. $VERSION
  Deploy spring boot app into coreos with docker

  $(usage)

  Options:
  -h, --help  Display this help message and exit.
  -e env      The environment name if exists.
  -r release  The version to deploy. Default is "lastest".
    Where 'release' is the .

_EOF_
  return
}

log() {
  echo "`date +%H:%M:%S.%N` >>> $1"
}

check_config() {
  release=${release:-"lastest"}
  app_name=${app_name:-"app"}
  build_dir=${build_dir:-"target"}
  hosts_var="${env_name}_hosts"
  hosts_list="${!hosts_var}"
  ssh_user=${ssh_user:-"core"}
  docker_id=${docker_id:-app_name}

  app_release_file="${build_dir}/${app_name}-${release}.jar"

  if [[ ! -d ${build_dir} ]]; then
    error_exit "Build directory not found: ${build_dir}"
  fi

  if [[ ! -f ${app_release_file} ]]; then
    error_exit "App file not found: ${app_release_file}"
  fi

  if [[ ${#hosts_list[@]} -eq 0 ]]; then
    error_exit "No hosts setted"
  fi
  
  cat <<- _EOF_
  
  Deploying using this configuration values and parameters
  --------------------------------------------------------
  release=${release}
  environment=${env_name}
  app_name=${app_name}
  build_dir=${build_dir}
  hosts=${hosts_list}
  ssh_user=${ssh_user}
  ssh_key=${ssh_key}
  docker_options=${docker_options}
  docker_id=${docker_id}
  --------------------------------------------------------
  
_EOF_
}

config() {
  if [[ ! -f deploy.cfg ]]; then
    error_exit "Deploy configuration not found!"
  fi

  . deploy.cfg
}

create_docker_file() {
  log "Creating docker file ..."
  mkdir ${docker_dir}
  
  if [[ $? -ne 0 ]]; then
    error_exit "Could not create ${docker_dir}"
  fi
  
  cat <<- _EOF_ > ${docker_dir}/AppDockerfile
FROM java:8
RUN mkdir -p ${app_dir}
VOLUME ${app_dir}
ENTRYPOINT ["java","-Djava.security.egd=file:/dev/./urandom","-jar","${app_dir}/${jar_file}"]
EXPOSE 8080
_EOF_
}

create_deploy_file() {
  log "Creating deploy file ..."
  cat <<- _EOF_ > deploy.sh
#!/bin/bash
exists=\`docker images | grep -wc ${docker_id}\`
running=\`docker ps | grep -wc ${docker_id}\`
if [[ \$running -eq 1 ]]; then
  echo "Stopping docker ${docker_id}"
  docker stop ${docker_id}
fi

cd ~/deploy

echo "Packaging ..."
cd pack
rm -f ../${jar_release}
zip -qr0 ../${jar_release} *

if [[ \$? -ne 0 ]]; then
  echo "Erro packaging jar"
  exit 1
fi

sudo mkdir -p ${app_dir}
sudo chown \$USER. ${app_dir} -R
rm -rf ${app_dir}/*
echo "${release}" > ${app_dir}/VERSION
echo "\`date\`" > ${app_dir}/STARTED_AT
chmod 444 ${app_dir}/*

cd ..
cp -v ~/deploy/${jar_release} ${app_dir}/${jar_file}

if [[ \$exists -eq 0 ]]; then
  echo "Building docker image ..."
  cd $docker_dir
  docker build -f AppDockerfile -t ${docker_id} .
fi
_EOF_
}

create_run_file() {
  log "Creating run file ..."
  cat <<- _EOF_ > runapp.sh
#!/bin/bash
c=\`docker ps -a | grep -wc ${docker_id}\`
s=\`docker ps | grep -wc ${docker_id}\`

if [[ \$s -ge 1 ]]; then
  echo "docker ${docker_id} is running"
  exit 1
fi

if [[ \$c -ge 1 ]]; then
  docker start ${docker_id}
else
  docker run -d -v ${app_dir}:${app_dir}:ro -e "SPRING_PROFILES_ACTIVE=${env_name}" --name="${docker_id}" ${docker_options} ${docker_id}
fi
_EOF_
}

prepare_deploy() {
  log "Creating deploy temp dir ..."
  project_dir=$PWD
  app_dir="/application"
  deploy_dir=".deploy_`uuidgen`"
  pack_dir="pack"
  docker_dir="docker"
  jar_release="${app_name}-${release}.jar"
  jar_file="${app_name}-running.jar"
  ssh_cmd="ssh"
  
  if [[ ${ssh_key:+"--"} == "--" ]]; then
    ssh_cmd="ssh -i ${ssh_key}"
  fi
    
  mkdir -p ${deploy_dir}/${pack_dir}
  cd ${deploy_dir}/${pack_dir}

  log "Unpacking jar ..."
  jar -xf $project_dir/${app_release_file}
  if [[ $? -ne 0 ]]; then
    error_exit "Erro unpacking jar"
  fi

  cd ..
  create_docker_file
  create_run_file
  create_deploy_file  
}

execute_deploy() {
  cd ${project_dir}
  echo "Executing deploy"
  for s in $hosts_list; do
    echo -n "Deploy to $s ? [y/n/c to cancel]: "
    read resp
    
    if [[ "${resp}" == "y" ]]; then  
      log "Syncing files ... to ${s}"
      rsync -crlt --progress --delete --force -e "${ssh_cmd}" $deploy_dir/* ${ssh_user}@${s}:~/deploy
      ${ssh_cmd} ${ssh_user}@${s} 'chmod u+x ~/deploy/*.sh; ~/deploy/deploy.sh; if [[ $? -eq 0 ]]; then ~/deploy/runapp.sh; fi'    
    elif [[ "${resp}" == "c" ]]; then
      log "Deploy canceled!"
      break
    fi
  done
}

# Trap signals
trap "signal_exit TERM" TERM HUP
trap "signal_exit INT"  INT

# Parse command-line
while [[ -n $1 ]]; do
  case $1 in
    -h | --help)
      help_message; graceful_exit ;;
    -e)
      shift; env_name="$1" ;;
    -r)
      shift; release="$1" ;;
    -* | --*)
      usage
      error_exit "Unknown option $1" ;;
    *)
      echo "Argument $1 to process..." ;;
  esac
  shift
done

# Main logic

config
check_config
prepare_deploy
execute_deploy
graceful_exit

