# imports {{{
import asyncio
import glob
import random
import subprocess
import time

from dbus_fast import Variant

import psutil

from libqtile import hook, layout, qtile, widget
from libqtile.backend.base import Internal
from libqtile.backend.wayland import InputConfig
from libqtile.backend.wayland.layer import LayerStatic
from libqtile.backend.wayland.xdgwindow import XdgStatic
from libqtile.bar import Bar
from libqtile.config import Click, Drag, Group, Key, Match, Screen
from libqtile.lazy import lazy
from libqtile.widget.base import _Widget

import mydbus
import mywidgets
# }}}


wmname = 'LG3D'


@hook.subscribe.startup_once
def startup(*args):
	subprocess.call(['~/.config/qtile/autostart'], shell=True)

#@hook.subscribe.resume
#def resume(*args):
#	subprocess.call(['swaylock'])


# inputs {{{
wl_input_rules = {
	'type:keyboard': InputConfig(kb_layout='de', kb_variant='deadgraveacute', kb_repeat_delay=250, kb_repeat_rate=60),
	'type:touchpad': InputConfig(natural_scroll=True, tap=True, dwt=True),
	# TODO: the below don't seem to do anything
	'1133:49299:Logitech Advanced Corded Mouse M500s Keyboard': InputConfig(kb_repeat_delay=1, kb_repeat_rate=20),
	'1133:49299:Logitech Advanced Corded Mouse M500s': InputConfig(kb_repeat_delay=1, kb_repeat_rate=20),
}


notif_id_brightness = 0
@lazy.function
def brightness(qtile, *, up):
	global notif_id_brightness
	r = subprocess.run(['brightnessctl', '-m', '-e', 'set', '+10%' if up else '10%-'], capture_output=True, text=True).stdout.split(',')
	curr = int(r[2])
	maxx = int(r[4])
	notif_id_brightness = mydbus.notify("backlight brightness", hints={'value': Variant('u', int(100 * curr / maxx))}, expire_timeout=1500, replaces_id=notif_id_brightness)

notif_id_volume = 0
@lazy.function
def volume(qtile, *, up):
	global notif_id_volume
	subprocess.run(['wpctl', 'set-volume', '@DEFAULT_AUDIO_SINK@', '2%+' if up else '2%-', '-l', '1.0'])
	if up: subprocess.run(['wpctl', 'set-mute', '@DEFAULT_AUDIO_SINK@', '0'])
	r = subprocess.run(['wpctl', 'get-volume', '@DEFAULT_AUDIO_SINK@'], capture_output=True, text=True).stdout.split(' ')
	if len(r) == 3 and r[2] == "[MUTED]": notif_id_volume = mydbus.notify("audio muted", expire_timeout=1500, replaces_id=notif_id_volume)
	else: notif_id_volume = mydbus.notify("audio volume", hints={'value': Variant('u', int(100 * float(r[1])))}, expire_timeout=1500, replaces_id=notif_id_volume)

notif_id_mute = 0
@lazy.function
def mute_toggle(qtile):
	global notif_id_mute
	subprocess.run(['wpctl', 'set-mute', '@DEFAULT_AUDIO_SINK@', 'toggle'])
	r = subprocess.run(['wpctl', 'get-volume', '@DEFAULT_AUDIO_SINK@']).stdout.split(' ')
	if len(r) == 3 and r[2] == "[MUTED]": notif_id_mute = mydbus.notify("audio muted", expire_timeout=1500, replaces_id=notif_id_mute)
	else: notif_id_mute = mydbus.notify("audio volume", hints={'value': Variant('u', int(100 * float(r[1])))}, expire_timeout=1500, replaces_id=notif_id_mute)


@lazy.function
def jump_undisplayed_group(qtile, *, forward):
	i = qtile.groups.index(qtile.current_group)
	l = len(qtile.groups)
	for j in range(1, l):
		k = ((i+j) if forward else (i-j)) % l
		if not qtile.groups[k].screen:
			qtile.groups[k].toscreen()
			break


wm = 'mod1'  # control qtile with Alt+X
launch = 'mod4'  # quick-launch stuff with Win+Y

keys = [
	Key([wm], 'i', jump_undisplayed_group(forward=False), desc="display previous group"),
	Key([wm], 'k', jump_undisplayed_group(forward=True), desc="display next group"),
	Key([wm], 'j', lazy.prev_screen(), desc="move focus to previous screen"),
	Key([wm], 'l', lazy.next_screen(), desc="move focus to next screen"),

	Key([launch], 't', lazy.spawn('kitty'), desc="[T]erminal emulator"),
	Key([launch], 'f', lazy.spawn('pcmanfm-qt'), desc="[F]ile browser"),
	Key([launch], 'e', lazy.spawn('nvim-qt'), desc="text [E]ditor"),
	Key([launch], 'a', lazy.spawn('pavucontrol-qt'), desc="Pulse[A]udio settings"),
	Key([launch], 'q', lazy.spawn('kitty bpytop'), desc="task manager (not [Q]ps)"),
	Key([launch], 'b', lazy.spawn('librewolf'), desc="web [B]rowser"),
	Key([launch], 'p', lazy.spawn('tor-browser-prompt'), desc="[P]rivacy-centric web browser (Tor Browser)"),
	Key([launch], 'k', lazy.spawn('keepassxc'), desc="password manager ([K]eePassXC)"),
	Key([launch], 's', lazy.spawn('signal-desktop --ozone-platform=wayland'), desc="show the [S]ignal window"),
	Key([launch], 'r', lazy.spawn('bemenu-run'), desc="[R]un"),

	Key([], 'XF86MonBrightnessUp', brightness(up=True)),
	Key([], 'XF86MonBrightnessDown', brightness(up=False)),

	Key([], 'XF86AudioRaiseVolume', volume(up=True)),
	Key([], 'XF86AudioLowerVolume', volume(up=False)),
	Key([], 'XF86AudioMute', mute_toggle()),

	# TODO: MPRIS

	Key([wm, 'control'], 'r', lazy.reload_config(), desc="reload qtile"),  # TODO: replace with inotify listener to automatically reload the config whenever it changes
	Key([wm, 'control'], 'q', lazy.shutdown(), desc="exit qtile"),
]
if qtile.core.name == "wayland": keys += [
	Key([launch], 'x', lazy.spawn('xeyes'), desc="[X]Eyes (if they follow your cursor the window is using X)"),
	Key([launch], 'l', lazy.spawn('swaylock'), desc="[L]ock screen"),
	Key([launch], 'Print', lazy.spawn('grim'), desc="take screenshot"),
]

mouse = []
# }}}


# windows {{{
follow_mouse_focus = True
bring_front_click = False
cursor_warp = False
auto_fullscreen = True
focus_on_window_activation = 'focus'

layouts = [
	layout.Bsp(border_width=0), #border_focus='#007fffbf', border_normal='#001f7fbf'),
	layout.Max(),
	# Try more layouts by unleashing below layouts.
	#layout.Stack(num_stacks=2),
	#layout.Columns(),
	#layout.Matrix(),
	#layout.MonadTall(),
	#layout.MonadWide(),
	#layout.RatioTile(),
	#layout.Tile(),
	#layout.TreeTab(),
	#layout.VerticalTile(),
	#layout.Zoomy(),
]

floating_layout = layout.Floating(float_rules=[
	*layout.Floating.default_float_rules,
	Match(func=lambda win: bool(win.is_transient_for())),
	Match(wm_class='zenity'), Match(wm_class='qarma'),
	Match(wm_class='org.keepassxc.KeePassXC'),
	Match(wm_class='pcmanfm-qt', title="Execute file"),
	Match(wm_class='pcmanfm-qt', title="Choose an Application"),
	Match(wm_class='pcmanfm-qt', title="Delete Files"), Match(wm_class='pcmanfm-qt', title="Move files"), Match(wm_class='pcmanfm-qt', title="Copy Files"), Match(wm_class='pcmanfm-qt', title="Rename File"),
	Match(wm_class='signal'), Match(wm_class='signal-desktop'),
	Match(wm_class='pavucontrol-qt'),
	Match(wm_class='firefox', title="Firefox — Sharing Indicator"),
	Match(wm_class='XEyes', title="xeyes"),
], border_width=2, border_focus='#ff7f00bf', border_normal='#7f1f00bf')


@hook.subscribe.client_new
def client_new(win):
	if isinstance(win, XdgStatic): win.opacity = .75  # TODO: this doesn't do anything. I want my dropdowns and context menus to be transparent!

@hook.subscribe.focus_change
def focus_change():
	for other in qtile.windows_map.values():
		if not isinstance(other, (Internal, LayerStatic, _Widget)):
			if other is qtile.current_window or "at.yrlf.wl_mirror" in other.get_wm_class():
				other.opacity = 1
			else:
				other.opacity = .75


NAVIGABLE_LAYOUTS = (
	'max',
)

#@lazy.function
#def switch_window_or_layer(qtile, *, next):
#	if qtile.current_window.floating or qtile.current_group.layout.name in NAVIGABLE_LAYOUTS


dgroups_key_binder = None
dgroups_app_rules = []  # type: list

groups = [
	Group("comms", exclusive=True, matches=[  # TODO: get a mail client that can minimize to tray, make this group non-exclusive
		Match(wm_class='thunderbird'),
		#Match(func=lambda win: win.floating),
	]),
	Group("dual screen enabler"),
]


@hook.subscribe.client_managed
def client_managed(win):
	if not isinstance(win, LayerStatic):
		win.group.toscreen()


@lazy.function
def move_window_to_group(qtile, *, next, switch_group=False, toggle=False):
	i = qtile.groups.index(qtile.current_group)
	if i == 0 and not next: return
	elif i == len(qtile.groups) - 1 and next:
		name = 'autogen-{}'.format(time.monotonic_ns())
		qtile.add_group(name)
	else: name = qtile.groups[i+1 if next else i-1].name
	qtile.current_window.togroup(name, switch_group=switch_group, toggle=toggle)


@lazy.function
def show_window_info(qtile):
	mydbus.notify("window info", "name: {}\nWM class: {}".format(qtile.current_window.name, qtile.current_window.get_wm_class()))


keys += [
	Key([wm], 'w', lazy.layout.up(), desc="move focus up"),
	Key([wm], 'a', lazy.layout.left(), desc="move focus left"),
	Key([wm], 's', lazy.layout.down(), desc="move focus down"),
	Key([wm], 'd', lazy.layout.right(), desc="move focus right"),
	Key([wm], 'Tab', lazy.group.next_window(), desc="move focus to next window"),

	Key([wm], 'x', lazy.window.toggle_floating(), desc="(un-)float window"),

	Key([wm], 'space', lazy.next_layout(), desc="(un-)maximize"),

	Key([wm, 'shift'], 'w', lazy.layout.grow_up(), desc="grow window up"),
	Key([wm, 'shift'], 'a', lazy.layout.grow_left(), desc="grow window left"),
	Key([wm, 'shift'], 's', lazy.layout.grow_down(), desc="grow window down"),
	Key([wm, 'shift'], 'd', lazy.layout.grow_right(), desc="grow window right"),

	Key([wm], 'F4', lazy.window.kill(), desc="close window"),

	Key([wm, 'shift'], 'i', move_window_to_group(next=False, switch_group=True), desc="move window to previous group"),
	Key([wm, 'shift'], 'k', move_window_to_group(next=True, switch_group=True), desc="move window to next group"),
]

mouse += [
	Drag([wm], 'Button1', lazy.window.set_position_floating(), start=lazy.window.get_position()),
	Drag([wm], 'Button3', lazy.window.set_size_floating(), start=lazy.window.get_size()),
	Click([wm], 'Button2', lazy.window.kill()),
	Click([wm, 'shift'], 'Button2', show_window_info()),
]
# }}}


# widgets {{{
widget_defaults = dict(
    font='Noto Sans',
    fontsize=10,
    foreground='#bfbfbf',
    padding=1,
)
extension_defaults = widget_defaults.copy()


class MultiCpuGraph(mywidgets._MultiGraph):
	def __init__(self, length, colors, **config):
		super().__init__(length, colors, min_value=0, max_value=100, log_scale=False, **config)

	def get_values(self):
		return psutil.cpu_percent(percpu=True)


class MultiNetGraph(mywidgets._MultiGraph):
	def __init__(self, length, col_dn, col_up, **config):
		super().__init__(length, [col_dn, col_up], min_value=0, **config)
		self.dn = 0
		self.up = 0

	def get_values(self):
		stat = psutil.net_io_counters(pernic=True)
		dDn = stat['eno1'].bytes_recv + stat['wlan0'].bytes_recv - self.dn
		dUp = stat['eno1'].bytes_sent + stat['wlan0'].bytes_sent - self.up
		if 'enp4s0f3u2' in stat:
			dDn += stat['enp4s0f3u2'].bytes_recv
			dUp += stat['enp4s0f3u2'].bytes_sent
		if 'enp4s0f3u3' in stat:
			dDn += stat['enp4s0f3u3'].bytes_recv
			dUp += stat['enp4s0f3u3'].bytes_sent
		self.dn += dDn
		self.up += dUp
		return dDn, dUp

	def draw(self):
		if any(any(hist) for hist in self.hists): return super().draw()

		# if there's no network traffic to plot: draw a big X
		self.drawer.clear(self.background or self.bar.background)

		self.drawer.set_source_rgb(self.foreground)
		size = min(self.width, self.height)
		self.drawer.ctx.move_to(.5*self.width, .5*self.height - .25*size)
		self.drawer.ctx.line_to(.5*self.width + .25*size, .5*self.height - .5*size)
		self.drawer.ctx.line_to(.5*self.width + .5*size, .5*self.height - .25*size)
		self.drawer.ctx.line_to(.5*self.width + .25*size, .5*self.height)
		self.drawer.ctx.line_to(.5*self.width + .5*size, .5*self.height + .25*size)
		self.drawer.ctx.line_to(.5*self.width + .25*size, .5*self.height + .5*size)
		self.drawer.ctx.line_to(.5*self.width, .5*self.height + .25*size)
		self.drawer.ctx.line_to(.5*self.width - .25*size, .5*self.height + .5*size)
		self.drawer.ctx.line_to(.5*self.width - .5*size, .5*self.height + .25*size)
		self.drawer.ctx.line_to(.5*self.width - .25*size, .5*self.height)
		self.drawer.ctx.line_to(.5*self.width - .5*size, .5*self.height - .25*size)
		self.drawer.ctx.line_to(.5*self.width - .25*size, .5*self.height - .5*size)
		self.drawer.ctx.fill()

		self.drawer.draw(offsetx=self.offsetx, offsety=self.offsety, width=self.width, height=self.height)
# }}}


reconfigure_screens = True

screens = [
	Screen(
		left=Bar([
			mywidgets.UnsavedChanges(),
			mywidgets.vertical_short(widget.Clock, update_interval=15, format="%a\n%d\n%b"),
			mywidgets.AnalogClock(padding=2),
			mywidgets.VGroupBox(bg_overrides={"comms": ('#3fff00', '#007f1f')}),  # ('#ff00bf', '#5f007f')
			MultiNetGraph(length=16, col_dn='#007fff', col_up='#ff7f00'),
			MultiCpuGraph(length=16, colors=['#ff0000', '#ff7f00', '#ffff00', '#7fff00', '#00ff00', '#00ff7f', '#00ffff', '#007fff', '#0000ff', '#7f00ff', '#ff00ff', '#ff007f']),
			mywidgets.vertical_short(mywidgets.BetterBattery, low_percent=15, high_percent=90),
			#mywidgets.MprisAllPlayersController(notify=False),  # TODO: mouse click callbacks
			widget.StatusNotifier(padding=4),
			mywidgets.vertical_stacking(widget.CurrentLayout),
			#widget.Spacer(background=['#000000bf', '#0000003f']),  # TODO: remove this once gradient works for the whole bar again
		], 24, background='#000000bf'),
		wallpaper=random.choice(glob.glob('Pictures/**/* (* × *).png', recursive=True)),
		#wallpaper='Pictures/Frankreichreise (4160 × 2340).png',
		wallpaper_mode='fill',
	),
	Screen(
		right=Bar([
			mywidgets.UnsavedChanges(),
			mywidgets.VGroupBox(bg_overrides={"comms": ('#3fff00', '#007f1f')}),
			mywidgets.vertical_stacking(widget.CurrentLayout),
		], 24, background='#000000bf'),
		wallpaper="Pictures/Games/FAST Racing NEO/" + random.choice([
			"Avalanche Valley.jpg",
			"Caldera Post.jpg",
			"Cameron Crest.jpg",
			"Daitoshi Station.jpg",
			"Guangzhou + Mueller.jpg",
			"Guangzhou + Willard.jpg",
			"Iceland.png",
			"Kenshu Jungle.jpg",
			"keyshot (NEO).jpg",
			"Kuiper Belt 1.png",
			"Kuiper Belt 2.png",
			"loopings.jpg",
			"Mori Park.png",
			"Mueller Pacific.jpg",
			"New Zendling.png",
			"parabolar antennae.jpg",
			"Pyramid Valley.png",
			"Scorpio Circuit.jpg",
			"Sendai Outpost.jpg",
			"Sunahara Plains.jpg",
			"Tepaneca Vale.jpg",
			"Zvil Raceway.jpg",
		]),
		wallpaper_mode='fill',
	),
]
