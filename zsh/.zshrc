export DOTFILESROOT=$HOME/git/dotfiles
# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block, everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi
source ${DOTFILESROOT}/zsh/globals.sh
source ${DOTFILESROOT}/zsh/scripts.sh
export HOSTNAME="$(hostname)"
if [[ $machine == 'Mac' ]]
then
  source ${DOTFILESROOT}/zsh/macconf.sh
  export ZSH="/Users/$(whoami)/.oh-my-zsh"
  export ANDROID_HOME="/Users/vibbix/Library/Android/sdk"
  ZSH_THEME="powerlevel10k/powerlevel10k"
  # g cloud
  # To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
  if [ -n "$SSH_CLIENT" ] || [ -n "$SSH_TTY" ] || [[ $TERM_PROGRAM = 'vscode' ]] || [ -n "$TMUX" ]; then
    ZSH_THEME="dieter"
  else
    ZSH_THEME="powerlevel10k/powerlevel10k"
    [[ -f ${DOTFILESROOT}/zsh/.p10k.zsh ]] && source ${DOTFILESROOT}/zsh/.p10k.zsh
  fi
  test -e '/usr/local/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh' && source /usr/local/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
  # Path to your oh-my-zsh installation.
  plugins=(docker macos web-search vscode tmux)
  test -e "${HOME}/.iterm2_shell_integration.zsh" && source "${HOME}/.iterm2_shell_integration.zsh"
  # pnpm
  export PNPM_HOME="/Users/mbeznos/Library/pnpm"
  case ":$PATH:" in
    *":$PNPM_HOME:"*) ;;
    *) export PATH="$PNPM_HOME:$PATH" ;;
  esac
  # pnpm end
else
  export ANDROID_HOME="$HOME/.android_home"
  export ZSH="/home/$(whoami)/.oh-my-zsh"
  plugins=(gitfast vscode tmux)
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
#[ -f /Users/vibbix/.travis/travis.sh ] && source /Users/vibbix/.travis/travis.sh
#source $DOTFILESROOT/zsh/gitstatus/gitstatus.prompt.zsh
[[ -s "$HOME/.workconf.sh" ]] && source "$HOME/.workconf.sh"
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh
[[ -s "$HOME/.gvm/scripts/gvm" ]] && source "$HOME/.gvm/scripts/gvm"
export PATH="/usr/local/opt/ant@1.9/bin:$PATH"
alias introduce="figlet -f slant -c $HOSTNAME | lolcat && neofetch"

# # To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
# [[ -f ~/.p10k.zsh ]] && source ~/.p10k.zsh

# export PATH="/Users/vibbix/.pyenv/bin:$PATH"
# eval "$(pyenv init -)"
# eval "$(pyenv virtualenv-init -)"
# export MSBuildSDKsPath=/usr/local/share/dotnet/sdk/3.0.101/Sdks

if [[ -d "$HOME/.sdkman" ]]; then
  export SDKMAN_DIR="$HOME/.sdkman"
  [[ -s "$SDKMAN_DIR/bin/sdkman-init.sh" ]] && source "$SDKMAN_DIR/bin/sdkman-init.sh"
fi

if [[ -d "$HOME/.nvm" ]]; then
  export NVM_DIR="$HOME/.nvm"
  if [[ $machine == 'Mac' ]]
  then
    [ -s "/opt/homebrew/opt/nvm/nvm.sh" ] && \. "/opt/homebrew/opt/nvm/nvm.sh"  # This loads nvm
    [ -s "/opt/homebrew/opt/nvm/etc/bash_completion.d/nvm" ] && \. "/opt/homebrew/opt/nvm/etc/bash_completion.d/nvm"  # This loads nvm bash_completion
  else 
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
    [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion
  fi
fi

if [[ -d "$HOME/.pyenv" ]]; then
  export PYENV_ROOT="$HOME/.pyenv"
  [[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
  eval "$(pyenv init -)"
fi

if [[ -d "$HOME/.dotnet" ]]; then
  export DOTNET_ROOT=$HOME/.dotnet
fi

alias rebasebranch='git fetch && git rebase origin/main && git push --force-with-lease'
