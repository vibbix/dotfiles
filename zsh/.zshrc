export DOTFILESROOT=$HOME/git/dotfiles
source ${DOTFILESROOT}/zsh/globals.sh
export HOSTNAME="$(hostname)"
if [[ $machine == 'Mac' ]]
then
  source ${DOTFILESROOT}/zsh/macconf.sh
  export D9HOME="/Users/vibbix/git/d9"
  export ZSH="/Users/$(whoami)/.oh-my-zsh"
  export ANDROID_HOME="/Users/vibbix/Library/Android/sdk"
  # g cloud
  if [ $(uname -n) = 'ma-mbeznos' ]; then
    # To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
    #[[ -f ${DOTFILESROOT}/zsh/.p10k.zsh ]] && source ${DOTFILESROOT}/zsh/.p10k.zsh
    ZSH_THEME="powerlevel10k/powerlevel10k"
  else
    source ${DOTFILESROOT}/zsh/powerline9kconf.sh
    ZSH_THEME="powerlevel9k/powerlevel9k"
   # virtualenv
    export WORKON_HOME=~/virtualenvs
    test -e '/usr/local/bin/virtualenvwrapper.sh' && source /usr/local/bin/virtualenvwrapper.sh
    POWERLEVEL9K_LEFT_PROMPT_ELEMENTS=(status os_icon dir vcs) #fix for MASSIVE git repo
  fi
  # Path to your oh-my-zsh installation.
  export NVM_DIR="$HOME/.nvm"
  plugins=(docker osx web-search vscode tmux)
  test -e '/usr/local/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh' && source /usr/local/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
  test -e "${HOME}/.iterm2_shell_integration.zsh" && source "${HOME}/.iterm2_shell_integration.zsh"
else
  export ANDROID_HOME="$HOME/.android_home"
  export ZSH="/home/$(whoami)/.oh-my-zsh"
  plugins=(gitfast vscode tmux)
fi
if [ -n "$SSH_CLIENT" ] || [ -n "$SSH_TTY" ] || [[ $TERM_PROGRAM = 'vscode' ]] || [ -n "$TMUX" ]; then
  ZSH_THEME="dieter"
fi

source $ZSH/oh-my-zsh.sh
function toiletfonts(){
    for i in ${TOILET_FONT_PATH:=/usr/share/figlet}/*.{t,f}lf; do j=${i##*/}; toilet -d "${i%/*}" -f "$j" "${j%.*}"; done    
}

#source $HOME/.cargo/env
export PATH=$GOPATH/bin:$HOME/bin:/usr/local/bin:$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools:$HOME/git/depot_tools:$HOME/flutter/bin:/usr/local/sbin:$HOME/flutter/bin:$PATH

[[ -s "/usr/local/share/zsh-autosuggestions/zsh-autosuggestions.zsh" ]] && source "/usr/local/share/zsh-autosuggestions/zsh-autosuggestions.zsh"

# fh - repeat history
fh() {
  print -z $( ([ -n "$ZSH_NAME" ] && fc -l 1 || history) | fzf +s --tac | sed 's/ *[0-9]* *//')
}
alias weather="curl https://wttr.in"


# added by travis gem
[ -f /Users/vibbix/.travis/travis.sh ] && source /Users/vibbix/.travis/travis.sh
#source $DOTFILESROOT/zsh/gitstatus/gitstatus.prompt.zsh
[[ -s "$HOME/.workconf.sh" ]] && source "$HOME/.workconf.sh"
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh
[[ -s "$HOME/.gvm/scripts/gvm" ]] && source "$HOME/.gvm/scripts/gvm"

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ -f ~/.p10k.zsh ]] && source ~/.p10k.zsh
