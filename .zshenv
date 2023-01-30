# adjust PATH
typeset -U path PATH
path=(~/.local/bin $path)
export PATH

# enable Wayland
export QT_QPA_PLATFORM=wayland
export SDL_VIDEODRIVER=wayland
export CLUTTER_BACKEND=wayland
export MOZ_ENABLE_WAYLAND=1

# disable X11
#unset DISPLAY

# needed for screen recording
export XDG_CURRENT_DESKTOP=qtile

# enable this fine IME
export GTK_IM_MODULE=fcitx
export SDL_IM_MODULE=fcitx
export QT_IM_MODULE=fcitx
export XMODIFIERS=@im=fcitx

# configure my style
export QT_STYLE_OVERRIDE=breeze
export XCURSOR_PATH=/usr/share/icons:~/.local/share/icons
export XCURSOR_THEME=breeze_cursors
export XCURSOR_SIZE=16

# configuration for stuff that doesn't use config files
export GRIM_DEFAULT_DIR=~/Pictures/Screenshots
export BEMENU_OPTS="-l 8 -w --scrollbar autohide --no-overlap --fn \"Noto Sans 10\"\
 --nb #000000bf --nf #bfbfbf\
 --tb #000000bf --tf #007fff\
 --fb #000000bf --ff #bfbfbf\
 --hb #1f1f1fbf --hf #007fff\
 --scb #000000bf --scf #007fff"