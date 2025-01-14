# adjust PATH
typeset -U path PATH
path=(~/.local/bin $path)
export PATH

export EDITOR=nvim

# enable Wayland
export QT_QPA_PLATFORM="wayland;xcb"
export SDL_VIDEODRIVER=wayland
export SDL_DYNAMIC_API=/usr/lib64/libSDL2-2.0.so
export CLUTTER_BACKEND=wayland
export MOZ_ENABLE_WAYLAND=1

# disable X11
#unset DISPLAY

# needed for screen recording
export XDG_CURRENT_DESKTOP=qtile

# needed by Java
export _JVM_AWT_WM_NONREPARENTING=1

# enable this fine IME
export QT_IM_MODULE=fcitx
export GTK_IM_MODULE=fcitx
export SDL_IM_MODULE=fcitx
export GLFW_IM_MODULE=ibus
export XMODIFIERS=@im=fcitx

# configuration for stuff that doesn't use config files
export GRIM_DEFAULT_DIR=~/Pictures/Screenshots
export GTK_THEME=Adwaita:dark
export BEMENU_OPTS="-fiw -l 8 --scrollbar autohide --no-overlap --monitor all --fn \"Noto Sans 10\" --margin 0 --border 0 --border-radius 0\
 --nb #000000bf --nf #bfbfbf\
 --ab #1f1f1fbf --af #bfbfbf\
 --tb #000000bf --tf #007fff\
 --fb #000000bf --ff #bfbfbf\
 --hb #001f3fbf --hf #007fff\
 --scb #1f1f1fbf --scf #007fff"
