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
#export TERM="screen-256color"
export TOILET_FONT_PATH="/usr/share/figlet"
export gorp="fuck off"
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh
export HOSTNAME="$(hostname)"
if [[ $machine == 'Mac' ]]
then
  export ZSH="/Users/$(whoami)/.oh-my-zsh"
  export ANDROID_HOME="/Users/vibbix/Library/Android/sdk"
  # g cloud
  if [ $(uname -n) = 'ma-lt-mbeznos' ]; then
    source $HOME/.workconf.sh
    POWERLEVEL9K_LEFT_PROMPT_ELEMENTS=(status os_icon dir ) #fix for MASSIVE git repo
  else
   # virtualenv
    export WORKON_HOME=~/virtualenvs
    source /usr/local/bin/virtualenvwrapper.sh
    POWERLEVEL9K_LEFT_PROMPT_ELEMENTS=(status os_icon dir vcs) #fix for MASSIVE git repo
  fi
  # Path to your oh-my-zsh installation.
  export NVM_DIR="$HOME/.nvm"
  plugins=(gitfast docker osx web-search vscode tmux)
  source /usr/local/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
  test -e "${HOME}/.iterm2_shell_integration.zsh" && source "${HOME}/.iterm2_shell_integration.zsh"
  test -e '/usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/path.zsh.inc' && source '/usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/path.zsh.inc'
  test -e '/usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/completion.zsh.inc' && source '/usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/completion.zsh.inc'
else
  export ANDROID_HOME="$HOME/.android_home"
  #ZSH_THEME="agnoster"
  export ZSH="/home/$(whoami)/.oh-my-zsh"
  #source ./zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
  plugins=(gitfast vscode tmux)
fi
export PATH=$GOPATH/bin:$HOME/bin:/usr/local/bin:$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools:$HOME/git/depot_tools:$HOME/flutter/bin:$PATH
if [ -n "$SSH_CLIENT" ] || [ -n "$SSH_TTY" ] || [[ $TERM_PROGRAM = 'vscode' ]] || [ -n "$TMUX" ]; then
  ZSH_THEME="dieter"
else
  ZSH_THEME="powerlevel9k/powerlevel9k"
fi
POWERLEVEL9K_MODE='awesome-fontconfig'
source $ZSH/oh-my-zsh.sh
alias gorp="toilet -d $TOILET_FONT_PATH -f 3d  \"$gorp\" | lolcat -t -a"
function toiletfonts(){
    for i in ${TOILET_FONT_PATH:=/usr/share/figlet}/*.{t,f}lf; do j=${i##*/}; toilet -d "${i%/*}" -f "$j" "${j%.*}"; done    
}
prompt_zsh_GPMSong () {
  if [[ $machine == 'Mac' ]]
  then
    conf=$(cat ~/Library/Application\ Support/Google\ Play\ Music\ Desktop\ Player/json_store/playback.json )
  else
    conf=$(cat ~/.config/Google\ Play\ Music\ Desktop\ Player/json_store/playback.json )
  fi
  playico=`echo '\UF04B'` # in orange
  state='false'
  if state=`echo $conf | jq '.playing' -r 2> /dev/null`; then
  else
    conf=`echo $conf | tr -cd '[:print:]'`
    state=`echo $conf | jq '.playing' -r 2> /dev/null`
  fi
  if [[ $state == "true" ]]; then
     artist=`echo $conf | jq '.song.artist' | tr -d '"'`;
     track=`echo $conf | jq '.song.title' | tr -d '"'`;
     echo -n "$playico $artist - $track";
  fi
}
#powerlevel9K specific changes
POWERLEVEL9K_CUSTOM_SONG="prompt_zsh_GPMSong"
POWERLEVEL9K_CUSTOM_SONG_BACKGROUND="009"
POWERLEVEL9K_CUSTOM_SONG_FOREGROUND="236"
POWERLEVEL9K_SHORTEN_DIR_LENGTH=3
POWERLEVEL9K_DIR_DEFAULT_FOREGROUND="236"
POWERLEVEL9K_SHORTEN_STRATEGY="truncate_middle"
# POWERLEVEL9K_LEFT_PROMPT_ELEMENTS=(status os_icon dir vcs)
if [[ `uname` == 'Darwin' ]]
then
  POWERLEVEL9K_RIGHT_PROMPT_ELEMENTS=(custom_song virtualenv load time)
else
  POWERLEVEL9K_RIGHT_PROMPT_ELEMENTS=(custom_song virtualenv load time)
fi
POWERLEVEL9K_MULTILINE_FIRST_PROMPT_PREFIX=""
POWERLEVEL9K_MULTILINE_SECOND_PROMPT_PREFIX="%{%B%F{yellow}%K{blue}%} ❯%{%b%f%k%F{blue}%}\UE0C0 %{%f%}"
POWERLEVEL9K_CHANGESET_HASH_LENGTH=5
POWERLEVEL9K_PROMPT_ON_NEWLINE=true
POWERLEVEL9K_BATTERY_LOW_BACKGROUND="black"
POWERLEVEL9K_BATTERY_CHARGING_BACKGROUND="black"
POWERLEVEL9K_BATTERY_CHARGED_BACKGROUND="black"
POWERLEVEL9K_BATTERY_DISCONNECTED_BACKGROUND="black"
POWERLEVEL9K_BATTERY_LOW_FOREGROUND="249"
POWERLEVEL9K_BATTERY_CHARGING_FOREGROUND="249"
POWERLEVEL9K_BATTERY_CHARGED_FOREGROUND="249"
POWERLEVEL9K_BATTERY_DISCONNECTED_FOREGROUND="249"
POWERLEVEL9K_BATTERY_LOW_VISUAL_IDENTIFIER_COLOR="red"
POWERLEVEL9K_BATTERY_CHARGING_VISUAL_IDENTIFIER_COLOR="yellow"
POWERLEVEL9K_BATTERY_CHARGED_VISUAL_IDENTIFIER_COLOR="green"
POWERLEVEL9K_BATTERY_DISCONNECTED_VISUAL_IDENTIFIER_COLOR="249"
POWERLEVEL9K_BATTERY_ICON="\uF240 "
POWERLEVEL9K_RUST_ICON="\uE7A8"
POWERLEVEL9K_TIME_BACKGROUND="white"
POWERLEVEL9K_TIME_FOREGROUND="black"
POWERLEVEL9K_TIME_FORMAT="%D{%H:%M:%S} \uF017"
POWERLEVEL9K_LEFT_SEGMENT_SEPARATOR='\uE0C0'
POWERLEVEL9K_RIGHT_SEGMENT_SEPARATOR='\UE0C2'
POWERLEVEL9K_LEFT_SUBSEGMENT_SEPARATOR='\uE0B1'
POWERLEVEL9K_RIGHT_SUBSEGMENT_SEPARATOR='\uE0B2'
#POWERLEVEL9K_MULTILINE_FIRST_PROMPT_PREFIX="%{%F{249}%}\u250f"
#POWERLEVEL9K_MULTILINE_SECOND_PROMPT_PREFIX="%{%F{249}%}\u2517%{%F{default}%} 

# System clipboard integration
#
# This file has support for doing system clipboard copy and paste operations
# from the command line in a generic cross-platform fashion.
#
# On OS X and Windows, the main system clipboard or "pasteboard" is used. On other
# Unix-like OSes, this considers the X Windows CLIPBOARD selection to be the
# "system clipboard", and the X Windows `xclip` command must be installed.

# clipcopy - Copy data to clipboard
#
# Usage:
#
#  <command> | clipcopy    - copies stdin to clipboard
#
#  clipcopy <file>         - copies a file's contents to clipboard
#
function clipcopy() {
  emulate -L zsh
  local file=$1
  if [[ $OSTYPE == darwin* ]]; then
    if [[ -z $file ]]; then
      pbcopy
    else
      cat $file | pbcopy
    fi
  elif [[ $OSTYPE == cygwin* ]]; then
    if [[ -z $file ]]; then
      cat > /dev/clipboard
    else
      cat $file > /dev/clipboard
    fi
  else
    if (( $+commands[xclip] )); then
      if [[ -z $file ]]; then
        xclip -in -selection clipboard
      else
 
       xclip -in -selection clipboard $file
      fi
    elif (( $+commands[xsel] )); then
      if [[ -z $file ]]; then
        xsel --clipboard --input 
      else
        cat "$file" | xsel --clipboard --input
      fi
    else
      print "clipcopy: Platform $OSTYPE not supported or xclip/xsel not installed" >&2
      return 1
    fi
  fi
}

# clippaste - "Paste" data from clipboard to stdout
#
# Usage:
#
#   clippaste   - writes clipboard's contents to stdout
#
#   clippaste | <command>    - pastes contents and pipes it to another process
#
#   clippaste > <file>      - paste contents to a file
#
# Examples:
#
#   # Pipe to another process
#   clippaste | grep foo
#
#   # Paste to a file
#   clippaste > file.txt
function clippaste() {
  emulate -L zsh
  if [[ $OSTYPE == darwin* ]]; then
    pbpaste
  elif [[ $OSTYPE == cygwin* ]]; then
    cat /dev/clipboard
  else
    if (( $+commands[xclip] )); then
      xclip -out -selection clipboard
    elif (( $+commands[xsel] )); then
      xsel --clipboard --output
    else
      print "clipcopy: Platform $OSTYPE not supported or xclip/xsel not installed" >&2
      return 1
    fi
  fi
}


function pet-select() {
  BUFFER=$(pet search --query "$LBUFFER")
  CURSOR=$#BUFFER
  zle redisplay
}
zle -N pet-select
bindkey '^s' pet-select



function prev() {
  PREV=$(fc -lrn | head -n 1)
  sh -c "pet new `printf %q "$PREV"`"
}

function create-shortcut(){
if [[ $# -le 1 || $# -ge 3 ]] ; then
    echo Usage: $0 '<namefile> <url>'
    echo
    echo Creates '<namefile>.url'.
    echo Openning '<namefile>.url' in Finder, under OSX, will open '<url>' in the default browser.
    exit 1
fi

file=$1.url
url=$2
echo '[InternetShortcut]' > $file
echo -n 'URL=' >> $file
echo $url >> $file
#echo 'IconIndex=0' >> $file

}
#source $HOME/.cargo/env
export PATH="/usr/local/sbin:$PATH"
[[ -s "$HOME/.gvm/scripts/gvm" ]] && source "$HOME/.gvm/scripts/gvm"
# [[ -s "/home/vibbix/.gvm/scripts/gvm" ]] && source "/home/vibbix/.gvm/scripts/gvm"

function initmappings(){
  ln -sf ~/git/dotfiles/hyper/.hyper.js ~/.hyper.js
  ln -sf ~/git/dotfiles/zsh/.zshrc ~/.zshrc
}

[[ -s "/usr/local/share/zsh-autosuggestions/zsh-autosuggestions.zsh" ]] && source "/usr/local/share/zsh-autosuggestions/zsh-autosuggestions.zsh"


# fh - repeat history
fh() {
  print -z $( ([ -n "$ZSH_NAME" ] && fc -l 1 || history) | fzf +s --tac | sed 's/ *[0-9]* *//')
}
alias weather="curl https://wttr.in"

export PATH="$HOME/flutter/bin:$PATH"

# added by travis gem
[ -f /Users/vibbix/.travis/travis.sh ] && source /Users/vibbix/.travis/travis.sh
