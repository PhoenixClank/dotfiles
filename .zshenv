# adjust PATH
typeset -U path PATH
path=(~/.local/bin $path)
export PATH

export EDITOR=nvim
export PAGER=less

# shitty shit
export VCPKG_DISABLE_METRICS=1
