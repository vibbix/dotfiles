#!/bin/sh
#check OS
unameOut="$(uname -s)"
case "${unameOut}" in
    Linux*)     machine=Linux;;
    Darwin*)    machine=Mac;;
    CYGWIN*)    machine=Cygwin;;
    MINGW*)     machine=MinGw;;
    *)          machine="UNKNOWN:${unameOut}"
esac
export GOPATH="$HOME/go"
export TOILET_FONT_PATH="/usr/share/figlet"
export gorp="fuck off"
alias gorp="toilet -d $TOILET_FONT_PATH -f 3d  \"$gorp\" | lolcat -t -a"
