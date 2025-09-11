# The following lines were added by compinstall
zstyle :compinstall filename '/home/felix/.zshrc'

autoload -Uz compinit
compinit
# End of lines added by compinstall


autoload -Uz add-zsh-hook


setopt AUTO_CD AUTO_PUSHD CD_SILENT PUSHD_IGNORE_DUPS PUSHD_SILENT
DIRSTACKSIZE=64

setopt COMPLETE_IN_WORD GLOB_COMPLETE LIST_PACKED NO_LIST_TYPES
LISTMAX=0
zstyle ':completion:*' menu select

setopt BAD_PATTERN GLOB_STAR_SHORT NOMATCH RC_EXPAND_PARAM NO_UNSET WARN_CREATE_GLOBAL WARN_NESTED_VAR

setopt NO_BANG_HIST HIST_FCNTL_LOCK HIST_IGNORE_ALL_DUPS HIST_LEX_WORDS HIST_NO_FUNCTIONS HIST_NO_STORE HIST_VERIFY SHARE_HISTORY
HISTFILE=~/.local/share/zsh/history
HISTSIZE=1024
SAVEHIST=1024
HISTORY_IGNORE='(fg|fg *)'
function should-history {
	emulate -L zsh
	# Should HISTORY_IGNORE use EXTENDED_GLOB syntax?
	#setopt EXTENDED_GLOB
	[[ $1 != ${~HISTORY_IGNORE} ]]
}
add-zsh-hook -Uz zshaddhistory should-history

setopt NO_FLOW_CONTROL

setopt AUTO_CONTINUE LONG_LIST_JOBS

setopt TRANSIENT_RPROMPT
PS1='[%B%F{%(?.green.red)}%3<<  %?%<<%f%b]%B%F{blue}%~%f%b%(!.#.$) '
PS2='%F{black}%~%B%F{blue}%5<<     %1_%<<%f%b> '
PROMPT_EOL_MARK='%B%S%(!.#.$)%s%b'
function blinky-cursor {
	case $TERM in
		linux)
			print -n '\e[?c'
			;;
		*)
			print -n '\e[5 q'
			;;
	esac
}
add-zsh-hook -Uz precmd blinky-cursor


#[[ "$COLORTERM" == (24bit|truecolor) || "${terminfo[colors]}" -eq '16777216' ]] || zmodload zsh/nearcolor


#bindkey -v  # for now

bindkey -N minimal .safe
bindkey -A minimal main

bindkey '^I' expand-or-complete  # must exist

# these are listed in terminfo(5) so they get set failsafely
[[ -n ${terminfo[khome]-} ]] && bindkey $terminfo[khome] vi-first-non-blank
[[ -n ${terminfo[kend]-} ]] && bindkey $terminfo[kend] vi-end-of-line
[[ -n ${terminfo[kcub1]-} ]] && bindkey $terminfo[kcub1] backward-char
[[ -n ${terminfo[kcuf1]-} ]] && bindkey $terminfo[kcuf1] forward-char
[[ -n ${terminfo[kcuu1]-} ]] && bindkey $terminfo[kcuu1] up-line-or-search
[[ -n ${terminfo[kcud1]-} ]] && bindkey $terminfo[kcud1] down-line-or-search
[[ -n ${terminfo[kbs]-} ]] && bindkey $terminfo[kbs] backward-delete-char
[[ -n ${terminfo[kdch1]-} ]] && bindkey $terminfo[kdch1] delete-char

# bracketed paste, veeery important
bindkey '\e[200~' bracketed-paste

# these may screw me up in different environments
bindkey '^H' backward-delete-word  # in Kitty in Wayland, Ctrl+Backspace actually types the Backspace character
bindkey '\e[3;5~' delete-word
bindkey '\e[1;5D' vi-backward-word
bindkey '\e[1;5C' vi-forward-word

#$@%* terminfo be #$@%* broken
bindkey '\e[A' up-line-or-search
bindkey '\e[B' down-line-or-search
bindkey '\e[C' forward-char
bindkey '\e[D' backward-char
bindkey '\e[F' vi-end-of-line
bindkey '\e[H' vi-first-non-blank

# searching
bindkey '^F' history-incremental-search-backward
[[ -n ${terminfo[kcuu1]-} ]] && bindkey -M isearch $terminfo[kcuu1] history-incremental-search-backward
[[ -n ${terminfo[kcud1]-} ]] && bindkey -M isearch $terminfo[kcud1] history-incremental-search-forward
[[ -n ${terminfo[kbs]-} ]] && bindkey -M isearch $terminfo[kbs] backward-delete-word  # actually delete character, rewind search to before character was typed
bindkey -M isearch '^M' accept-search
bindkey -M isearch '\e[A' history-incremental-search-backward
bindkey -M isearch '\e[B' history-incremental-search-forward
# Why did you not tell me about '.self-insert' and that it is different from 'self-insert' in this context?
bindkey -M isearch -R ' -~' self-insert

#typeset -g -A key
#key[Home]="${terminfo[khome]}"
#key[End]="${terminfo[kend]}"
#key[Backspace]="${terminfo[kbs]}"
#key[Delete]="${terminfo[kdch1]}"
#key[Up]="${terminfo[kcuu1]}"
#key[Down]="${terminfo[kcud1]}"
#key[Left]="${terminfo[kcub1]}"
#key[Right]="${terminfo[kcuf1]}"
#key[Control-Left]="${terminfo[kLFT5]}"
#key[Control-Right]="${terminfo[kRIT5]}"
#autoload -Uz up-line-or-beginning-search down-line-or-beginning-search
#zle -N up-line-or-beginning-search
#zle -N down-line-or-beginning-search
#[[ -n "${key[Home]}" ]] && bindkey -- "${key[Home]}" beginning-of-line
#[[ -n "${key[End]}" ]] && bindkey -- "${key[End]}" end-of-line
#[[ -n "${key[Backspace]}" ]] && bindkey -- "${key[Backspace]}" backward-delete-char
#[[ -n "${key[Delete]}" ]] && bindkey -- "${key[Delete]}" delete-char
#[[ -n "${key[Up]}" ]] && bindkey -- "${key[Up]}" up-line-or-beginning-search
#[[ -n "${key[Down]}" ]] && bindkey -- "${key[Down]}" down-line-or-beginning-search
#[[ -n "${key[Left]}" ]] && bindkey -- "${key[Left]}" backward-char
#[[ -n "${key[Right]}" ]] && bindkey -- "${key[Right]}" forward-char
#[[ -n "${key[Control-Left]}" ]] && bindkey -- "${key[Control-Left]}" backward-word
#[[ -n "${key[Control-Right]}" ]] && bindkey -- "${key[Control-Right]}" forward-word
#if (( ${+terminfo[smkx]} && ${+terminfo[rmkx]} )); then
#	autoload -Uz add-zle-hook-widget
#	function zle_application_mode_start { echoti smkx }
#	function zle_application_mode_stop { echoti rmkx }
#	add-zle-hook-widget -Uz zle-line-init zle_application_mode_start
#	add-zle-hook-widget -Uz zle-line-finish zle_application_mode_stop
#fi

# helpful help
autoload -Uz run-help run-help-git
(( ${+aliases[run-help]} )) && unalias run-help
alias help=run-help

# aliases
alias ls='ls --color=auto --group-directories-first -vGh'
alias hexdump='hexdump -f ~/.config/hexdump'
