import random
import subprocess
import time

from dbus_next import Variant

import psutil

from libqtile import hook, layout, qtile, widget
from libqtile.backend.base import Internal
from libqtile.backend.wayland import InputConfig
from libqtile.backend.wayland.layer import LayerStatic
from libqtile.bar import Bar
from libqtile.config import Click, Drag, Group, Key, Match, Screen
from libqtile.lazy import lazy
from libqtile.widget.base import _Widget

import mydbus
import mywidgets



################################################################################
#                               config variables                               #
################################################################################

dgroups_key_binder = None
dgroups_app_rules = []  # type: list
follow_mouse_focus = True
bring_front_click = False
cursor_warp = False
auto_fullscreen = True
focus_on_window_activation = 'focus'
reconfigure_screens = True
wmname = 'LG3D'



################################################################################
#                               startupp-y stuff                               #
################################################################################

@hook.subscribe.startup
def startup(*args):
	subprocess.call(['~/.config/qtile/autostart'], shell=True)

#@hook.subscribe.resume
#def resume(*args):
#	subprocess.call(['swaylock'])



################################################################################
#                                    inputs                                    #
################################################################################

wl_input_rules = {
	'type:keyboard': InputConfig(kb_layout='de', kb_variant='deadgraveacute', kb_repeat_delay=250, kb_repeat_rate=60),
	'type:touchpad': InputConfig(natural_scroll=True, tap=True),
}


BACKLIGHT_NAME = 'amdgpu_bl0'

with open('/sys/class/backlight/{}/max_brightness'.format(BACKLIGHT_NAME)) as f:
	BRIGHT_MAX = int(f.read())

bright_notif_id = 0
@lazy.function
def brightness(qtile, *, up):
	global bright_notif_id
	with open('/sys/class/backlight/{}/brightness'.format(BACKLIGHT_NAME), 'r+t') as f:
		bright_curr = int(f.read())

		if up: bright_next = min(BRIGHT_MAX, int((bright_curr + 1) * 2 - 1))
		else: bright_next = max(0, int((bright_curr + 1) / 2 - 1))

		f.truncate(0)
		print(int(bright_next), file=f)

		bright_notif_id = mydbus.notify("backlight brightness", hints={'value': Variant('u', int(100 * (bright_next - bright_min) / (bright_max - bright_min)))}, expire_timeout=1500, replaces_id=bright_notif_id)


wm = 'mod1' # control qtile with Alt+X
launch = 'mod4' # quick-launch stuff with Win+Y

keys = [
	Key([launch], 't', lazy.spawn('kitty'), desc="[T]erminal emulator"),
	Key([launch], 'f', lazy.spawn('pcmanfm-qt'), desc="[F]ile browser"),
	Key([launch], 'e', lazy.spawn('featherpad'), desc="text [E]ditor"),
	Key([launch], 'a', lazy.spawn('pavucontrol-qt'), desc="Pulse[A]udio settings"),
	Key([launch], 'q', lazy.spawn('kitty bpytop'), desc="task manager (not [Q]ps)"),
	Key([launch], 'b', lazy.spawn('firefox'), desc="web [B]rowser"),
	Key([launch], 'p', lazy.spawn('/home/felix/tor-browser-prompt'), desc="[P]rivacy-centric browser (Tor Browser)"),
	Key([launch], 'k', lazy.spawn('keepassxc'), desc="password manager ([K]eePassXC)"),
	Key([launch], 'x', lazy.spawn('xeyes'), desc="[X]Eyes (if they follow your cursor the window is using X)"),

	Key([launch], 'r', lazy.spawn('bemenu-run'), desc="[R]un"),

	Key([launch], 'l', lazy.spawn('swaylock'), desc="[L]ock screen"),

	Key([launch], 'Print', lazy.spawn('grim'), desc="take screenshot"),

	Key([], 'XF86MonBrightnessUp', brightness(up=True)),
	Key([], 'XF86MonBrightnessDown', brightness(up=False)),

	# TODO: volume

	# TODO: MPRIS

	Key([wm, 'control'], 'r', lazy.reload_config(), desc="reload qtile"),
	Key([wm, 'control'], 'q', lazy.shutdown(), desc="exit qtile"),
]

mouse = []



################################################################################
#                                   windows                                    #
################################################################################

layouts = [
	layout.Bsp(border_width=0),
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
	Match(wm_class='zenity'),
	Match(wm_class='firefox', title="Firefox — Sharing Indicator"),
	Match(wm_class='XEyes', title="xeyes"),
], border_width=2, border_focus='#ff7f00', border_normal='#bf1f00')


@hook.subscribe.focus_change
def focus_change():
	for other in qtile.windows_map.values():
		if other is qtile.current_window or isinstance(other, (Internal, LayerStatic, _Widget)):
			other.opacity = 1
		else:
			other.opacity = .75


groups = [
	Group("comms", exclusive=True, matches=[
		Match(wm_class='thunderbird'),
		Match(wm_class='signal'),
		Match(wm_class='signal-desktop'),
		Match(func=lambda win: win.floating),
	]),
	Group("dual screen enabler"),
]


@hook.subscribe.client_managed
def client_managed(win):
	if not isinstance(win, LayerStatic):
		win.group.cmd_toscreen()


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
	Key([wm], 'Tab', lazy.layout.next(), desc="move focus to next window"),

	Key([wm], 'x', lazy.window.toggle_floating(), desc="(un-)float window"),

	Key([wm], 'space', lazy.next_layout(), desc="(un-)maximize"),

	Key([wm, 'shift'], 'w', lazy.layout.grow_up(), desc="grow window up"),
	Key([wm, 'shift'], 'a', lazy.layout.grow_left(), desc="grow window left"),
	Key([wm, 'shift'], 's', lazy.layout.grow_down(), desc="grow window down"),
	Key([wm, 'shift'], 'd', lazy.layout.grow_right(), desc="grow window right"),

	Key([wm], 'F4', lazy.window.kill(), desc="close window"),

	Key([wm], 'i', lazy.screen.prev_group(), desc="display previous group"),
	Key([wm], 'k', lazy.screen.next_group(), desc="display next group"),

	Key([wm, 'shift'], 'i', move_window_to_group(next=False, switch_group=True), desc="move window to previous group"),
	Key([wm, 'shift'], 'k', move_window_to_group(next=True, switch_group=True), desc="move window to next group"),
]

mouse += [
	Drag([wm], 'Button1', lazy.window.set_position_floating(), start=lazy.window.get_position()),
	Drag([wm], 'Button3', lazy.window.set_size_floating(), start=lazy.window.get_size()),
	Click([wm], 'Button2', lazy.window.kill()),
	Click([wm, 'shift'], 'Button2', show_window_info()),
]



################################################################################
#                                     bar                                      #
################################################################################

widget_defaults = dict(
    font='Noto Sans',
    fontsize=10,
    foreground='#bfbfbf',
    padding=1,
)
extension_defaults = widget_defaults.copy()


class MultiCpuGraph(mywidgets._MultiGraph):
	def __init__(self, length, colors, **config):
		mywidgets._MultiGraph.__init__(self, length, colors, min_value=0, max_value=100, log_scale=False, **config)

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
		self.dn += dDn
		self.up += dUp
		return dDn, dUp

	def draw(self):
		if any(any(hist) for hist in self.hists): return super().draw()

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


screens = [
	Screen(
		left=Bar([
			mywidgets.UnsavedChanges(),
			mywidgets.vertical_short(widget.Clock, update_interval=15, format="%a\n%d\n%b"),
			mywidgets.AnalogClock(padding=2),
			mywidgets.VGroupBox(bg_overrides={"comms": ('#3fff00', '#00bf3f')}),
			MultiNetGraph(length=16, col_dn='#007fff', col_up='#ff7f00'),
			MultiCpuGraph(length=16, colors=['#ff0000', '#ff7f00', '#ffff00', '#7fff00', '#00ff00', '#00ff7f', '#00ffff', '#007fff', '#0000ff', '#7f00ff', '#ff00ff', '#ff007f']),
			mywidgets.vertical_short(mywidgets.BetterBattery),
			mywidgets.MprisAllPlayersController(notify=False),  # TODO: mouse click callbacks
			widget.StatusNotifier(),  # TODO: why does Signal not show up?
			mywidgets.vertical_stacking(widget.CurrentLayout),
		], 24, background='#000000bf'),
		wallpaper="~/Pictures/Games/FAST Racing NEO/" + random.choice([
			"Avalanche Valley.jpg",
			"Caldera Post.jpg",
			"Cameron Crest.jpg",
			"Daitoshi Station.jpg",
			"Iceland.png",
			"Kenshu Jungle.jpg",
			"keyshot (NEO).jpg",
			"Kuiper Belt 1.png",
			"Kuiper Belt 2.png",
			"Mori Park.png",
			"Mueller Pacific.jpg",
			"New Zendling.png",
			"Pyramid Valley.png",
			"Scorpio Circuit.jpg",
			"Sendai Outpost.jpg",
			"Sunahara Plains.jpg",
			"Tepaneca Vale.jpg",
			"Zvil Raceway.jpg",
		]),
		wallpaper_mode='fill',
	),
	Screen(
		right=Bar([
			mywidgets.UnsavedChanges(),
			mywidgets.VGroupBox(),
			mywidgets.vertical_stacking(widget.CurrentLayout),
		], 24, background='#000000bf'),
		wallpaper="~/Pictures/Games/Pokémon/fanart/Lenov/" + random.choice([
			"Shizu the Ninetails/lying (4096 × 2304).png",
			"Xiba the Gardevoir goddess/goddess (5328 × 2997).png",
			"Xiba the Gardevoir goddess/kirlia (4096 × 2304).png",
			"Kirlia & some ghost valentine (4208 × 2367).png",
			#"Linna & Lizzy sleepover (NSFW) 2 (4096 × 2304).png",
			"Linna & Midori gigantamax (3840 × 2160).png",
			"Linna & Midori river (4800 × 2700).png",
			#"party night (NSFW) (4096 × 2304).png",
			"Reshiram & Zekrom (4688 × 2637).png",
			#"Suicune (NSFW) (4096 × 2304).png",
			"Xerneas (4096 × 2304).png",
		]),
		wallpaper_mode='fill',
	),
]