#!/bin/sh

function create-shortcut(){
if [[ $# -le 1 || $# -ge 3 ]] ; then
    echo Usage: $0 '<namefile> <url>'
    echo
    echo Creates '<namefile>.url'.
    echo Opening '<namefile>.url' in Finder, under OSX, will open '<url>' in the default browser.
    exit 1
fi

file=$1.url
url=$2
echo '[InternetShortcut]' > $file
echo -n 'URL=' >> $file
echo $url >> $file
#echo 'IconIndex=0' >> $file
}

function initmappings(){
  ln -sf ~/git/dotfiles/hyper/.hyper.js ~/.hyper.js
  ln -sf ~/git/dotfiles/zsh/.zshrc ~/.zshrc
  ln -s ~/git/dotfiles/vscode/settings.json ~/Library/Application\ Support/Code/User/settings.json
}