POWERLEVEL9K_MODE='awesome-fontconfig'
export GOPATH="$HOME/go"
export TERM="screen-256color"
export TOILET_FONT_PATH="/usr/share/figlet"
export gorp="fuck off"
export PATH=$GOPATH/bin:$HOME/bin:/usr/local/bin:$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools:$PATH
export ANDROID_HOME="/Users/vibbix/Library/Android/sdk"
# Path to your oh-my-zsh installation.
export ZSH=/Users/vibbix/.oh-my-zsh
export NVM_DIR="$HOME/.nvm"
# Set name of the theme to load. Optionally, if you set this to "random"
# it'll load a random theme each time that oh-my-zsh is loaded.
# See https://github.com/robbyrussell/oh-my-zsh/wiki/Themes
ZSH_THEME="powerlevel9k/powerlevel9k"

# Which plugins would you like to load? (plugins can be found in ~/.oh-my-zsh/plugins/*)
# Custom plugins may be added to ~/.oh-my-zsh/custom/plugins/
# Example format: plugins=(rails git textmate ruby lighthouse)
# Add wisely, as too many plugins slow down shell startup.
plugins=(gitfast docker osx web-search vscode)
#ZSH_TMUX_AUTOSTART="true"
#ZSH_TMUX_ITERM2="true"
source $ZSH/oh-my-zsh.sh

# User configuration

# export MANPATH="/usr/local/man:$MANPATH"

# You may need to manually set your language environment
# export LANG=en_US.UTF-8

# Preferred editor for local and remote sessions
# if [[ -n $SSH_CONNECTION ]]; then
#   export EDITOR='vim'
# else
#   export EDITOR='mvim'
# fi

# Compilation flags
# export ARCHFLAGS="-arch x86_64"

# ssh
# export SSH_KEY_PATH="~/.ssh/rsa_id"

# Set personal aliases, overriding those provided by oh-my-zsh libs,
# plugins, and themes. Aliases can be placed here, though oh-my-zsh
# users are encouraged to define aliases within the ZSH_CUSTOM folder.
# For a full list of active aliases, run `alias`.
#
# Example aliases
# alias zshconfig="mate ~/.zshrc"
# alias ohmyzsh="mate ~/.oh-my-zsh"
alias gorp="toilet -d $TOILET_FONT_PATH -f 3d  \"$gorp\" | lolcat -t -a"
function toiletfonts(){
    for i in ${TOILET_FONT_PATH:=/usr/share/figlet}/*.{t,f}lf; do j=${i##*/}; toilet -d "${i%/*}" -f "$j" "${j%.*}"; done    
}
prompt_zsh_GPMSong () {
  #if [`uname -s` = "Darwin"]; then
    conf=$(cat ~/Library/Application\ Support/Google\ Play\ Music\ Desktop\ Player/json_store/playback.json )
  #else
  #fi
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
source /usr/local/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
test -e "${HOME}/.iterm2_shell_integration.zsh" && source "${HOME}/.iterm2_shell_integration.zsh"
#powerlevel9K specific changes
POWERLEVEL9K_CUSTOM_SONG="prompt_zsh_GPMSong"
POWERLEVEL9K_CUSTOM_SONG_BACKGROUND="009"
POWERLEVEL9K_CUSTOM_SONG_FOREGROUND="236"
POWERLEVEL9K_SHORTEN_DIR_LENGTH=3
POWERLEVEL9K_DIR_DEFAULT_FOREGROUND="236"
POWERLEVEL9K_SHORTEN_STRATEGY="truncate_middle"
POWERLEVEL9K_LEFT_PROMPT_ELEMENTS=(status os_icon context dir vcs)
#POWERLEVEL9K_LEFT_PROMPT_ELEMENTS=(icons_test)
POWERLEVEL9K_RIGHT_PROMPT_ELEMENTS=(custom_song load battery time)
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
