import asyncio
from collections import defaultdict, namedtuple
from datetime import datetime
import functools
import math
import os
import sys
import traceback as tb

from dbus_fast import Variant
from dbus_fast.aio import MessageBus

import psutil

from libqtile import bar, hook, widget
from libqtile.command.base import expose_command
from libqtile.log_utils import logger
from libqtile.widget import base

import mydbus


def vertical_short(cls, **config):
	"""Returns a text widget that displays right-side-up in a vertical bar.

	Takes as arguments the class of the widget and the config to pass to its constructor.
	To be used like `vertical_short(widget.Clock, format='xyz', update_interval=42)`.

	Care should be taken to configure the widget in such a way that its text fits into the bar.
	"""
	class Temp(cls):
		orientations = base.ORIENTATION_VERTICAL

		def calculate_length(self):
			if self.text:
				return min(self.layout.height, self.bar.height) + self.actual_padding * 2
			else:
				return 0

		def draw(self):
			if not self.can_draw():
				return
			self.drawer.clear(self.background or self.bar.background)
			self.layout.draw(
				int(self.bar.width / 2 - self.layout.width / 2) + 1,
				self.actual_padding or 0
			)
			self.drawer.draw(offsetx=self.offsetx, offsety=self.offsety, width=self.width, height=self.height)

		@expose_command()
		def update(self, text):
			if self.text == text:
				return
			if text is None:
				text = ""

			old_height = self.layout.height
			self.text = text

			if self.layout.height == old_height:
				self.draw()
			else:
				self.bar.draw()

	return Temp(**config)

def vertical_stacking(cls, **config):
	"""Returns a text widget that displays right-side-up in a vertical bar.

	The difference to `vertical_short` is that this one automatically adds line breaks between all of its letters.
	"""
	class Temp(cls):
		orientations = base.ORIENTATION_VERTICAL

		@property
		def text(self):
			return "\n".join(self._text)

		@text.setter
		def text(self, value):
			if len(value) > self.max_chars > 0:
				value = value[:self.max_chars] + "\u2026"
			self._text = value
			if self.layout:
				self.layout.text = self.formatted_text

		@property
		def formatted_text(self):
			return "\n".join(self.fmt.format(self._text))

		def calculate_length(self):
			if self.text:
				return min(self.layout.height, self.bar.height) + self.actual_padding * 2
			else:
				return 0

		def draw(self):
			if not self.can_draw():
				return
			self.drawer.clear(self.background or self.bar.background)
			self.layout.draw(
				int(self.bar.width / 2 - self.layout.width / 2) + 1,
				self.actual_padding or 0
			)
			self.drawer.draw(offsetx=self.offsetx, offsety=self.offsety, width=self.width, height=self.height)

		@expose_command()
		def update(self, text):
			if self.text == text:
				return
			if text is None:
				text = ""

			old_height = self.layout.height
			self.text = text

			if self.layout.height == old_height:
				self.draw()
			else:
				self.bar.draw()

	return Temp(**config)


class _MultiGraph(base._Widget):
	"""Plot multiple lines in a single graph."""
	orientations = base.ORIENTATION_BOTH
	defaults = [
		('hist_length', 30, "history length"),
		('update_interval', 1, "update interval in seconds"),
		('min_value', 0, "minimum value the samples can take. Dynamically calculated if `None`"),
		('max_value', None, "maximum value the samples can take. Dynamically calculated if `None`"),
		('log_scale', False, "whether to use a logarithmic scale instead of a linear one"),
		# TODO: draw x axis
	]

	def __init__(self, length, colors, **config):
		base._Widget.__init__(self, length, **config)
		self.add_defaults(_MultiGraph.defaults)
		self.colors = colors
		self.hists = tuple([(self.min_value or 0) for x in range(self.hist_length)] for color in self.colors)
		self._min = self.min_value or 0
		self._max = self.max_value or 0
		if self._max == self._min:
			self._max = self._min + 1

	def get_values(self):
		"""Returns a tuple that holds the current values.

		Subclasses must implement this method.
		"""
		raise NotImplementedError

	def timer_setup(self):
		self.timeout_add(self.update_interval, self.update)

	def update(self):
		for hist, sample in zip(self.hists, self.get_values()):
			hist.pop(0)
			hist.append(math.log(sample, 2) if self.log_scale else sample)
		if self.min_value is None:
			self._min = min(min(hist) for hist in self.hists)
		if self.max_value is None:
			self._max = max(max(hist) for hist in self.hists)
		if self._max == self._min:
			self._max = self._min + 1
		self.draw()
		self.timeout_add(self.update_interval, self.update)

	def draw(self):
		self.drawer.clear(self.background or self.bar.background)
		for hist, color in zip(self.hists, self.colors):
			self.drawer.set_source_rgb(color)
			self.drawer.ctx.move_to(0, self.height * (1 - (hist[0] - self._min) / (self._max - self._min)))
			for x, y in enumerate(hist[1:]):
				self.drawer.ctx.line_to((x + 1) * self.width / self.hist_length, self.height * (1 - (y - self._min) / (self._max - self._min)))
			self.drawer.ctx.stroke()
		self.drawer.draw(offsetx=self.offsetx, offsety=self.offsety, width=self.width, height=self.height)


class AsyncMixin:
	"""Adds a `timeout_add_async` method to your widget so you can call a coroutine in a timed loop."""
	def __init__(self):
		self._tasks = set()

	def timeout_add_async(self, secs, coro):
		task = asyncio.create_task(self._wait_then(secs, coro))
		self._tasks.add(task)
		task.add_done_callback(self._tasks.discard)

	async def _wait_then(self, secs, coro):
		if secs > 0: await asyncio.sleep(secs)
		try:
			await coro
		except Exception as exc:
			logger.error("widget async timeout crashed with {0} (at {1.filename}:{1.lineno})".format(tb.format_exception_only(exc)[0][:-1], tb.extract_tb(sys.exc_info()[2], -1)[0]))


class UnsavedChanges(widget.Image):
	def _configure(self, *args, **kwargs):
		super()._configure(*args, **kwargs)
		hook.subscribe.focus_change(self.hook_response)
		hook.subscribe.client_name_updated(self.hook_response)

	def hook_response(self, *args, **kwargs):
		self.update('~/Pictures/archlinux-logo-ff7f00.svg' if self.qtile.current_window and "*" in self.qtile.current_window.name else '~/Pictures/archlinux-logo-007fff.svg')


class AnalogClock(base._Widget, base.PaddingMixin):
	"""A graphical, circular clock with up to three hands."""
	orientations = base.ORIENTATION_BOTH
	defaults = [
		('update_interval', 15, "update interval in seconds"),
		#('foreground', '#bfbfbf', "color of everything except for the seconds hand"),
		('seconds_hand_color', '#ff0000', "color of the seconds hand"),
		('line_width', 2, "with of everything except for the minute ticks and the seconds hand"),
		('seconds_hand_width', 1, "width of the minute ticks and the seconds hand"),
		('draw_circle', False, "whether to draw a circle around the clock"),
		('hour_ticks_size', 0, "size of the hour ticks"),
		('minute_ticks_size', 0, "size of the minute ticks"),
		('hours_hand_length', .625, "length of the hours hand"),
		('minutes_hand_length', 1, "length of the minutes hand"),
		('seconds_hand_length', 0, "length of the seconds hand"),
	]

	def __init__(self, **config):
		base._Widget.__init__(self, bar.CALCULATED, **config)
		self.add_defaults(AnalogClock.defaults)
		self.add_defaults(base.PaddingMixin.defaults)

	def calculate_length(self):
		return self.bar.size

	def timer_setup(self):
		self.timeout_add(self.update_interval, self.update)

	def update(self):
		self.draw()
		self.timeout_add(self.update_interval, self.update)

	def draw(self):
		now = datetime.now()

		self.drawer.clear(self.background or self.bar.background)

		self.drawer.set_source_rgb(self.foreground)
		self.drawer.ctx.set_line_width(self.line_width)

		if self.draw_circle:
			self.drawer.ctx.arc(self.width / 2, self.height / 2, self.length / 2 - self.padding, 0, 2 * math.pi)

		if self.hour_ticks_size > 0:
			for i in range(12):
				dx = math.sin(i * math.pi / 6) * (self.length / 2 - self.padding)
				dy = -math.cos(i * math.pi / 6) * (self.length / 2 - self.padding)
				self.drawer.ctx.move_to(self.width / 2 + dx, self.height / 2 + dy)
				self.drawer.ctx.line_to(self.width / 2 + (1 - self.hour_ticks_size) * dx, self.height / 2 + (1 - self.hour_ticks_size) * dy)

		if self.hours_hand_length > 0:
			self.drawer.ctx.move_to(self.width / 2, self.height / 2)
			self.drawer.ctx.line_to(
				self.width / 2 + math.sin((now.hour + now.minute / 60) * math.pi / 6) * self.hours_hand_length * (self.length / 2 - self.padding),
				self.height / 2 - math.cos((now.hour + now.minute / 60) * math.pi / 6) * self.hours_hand_length * (self.length / 2 - self.padding)
			)

		if self.minutes_hand_length > 0:
			self.drawer.ctx.move_to(self.width / 2, self.height / 2)
			self.drawer.ctx.line_to(
				self.width / 2 + math.sin((now.minute + now.second / 60) * math.pi / 30) * self.minutes_hand_length * (self.length / 2 - self.padding),
				self.height / 2 - math.cos((now.minute + now.second / 60) * math.pi / 30) * self.minutes_hand_length * (self.length / 2 - self.padding)
			)

		self.drawer.ctx.stroke()
		self.drawer.ctx.set_line_width(self.seconds_hand_width)

		if self.minute_ticks_size > 0:
			for i in range(60):
				dx = math.sin(i * math.pi / 30) * (self.length / 2 - self.padding)
				dy = -math.cos(i * math.pi / 30) * (self.length / 2 - self.padding)
				self.drawer.ctx.move_to(self.width / 2 + dx, self.height / 2 + dy)
				self.drawer.ctx.line_to(self.width / 2 + (1 - self.minute_ticks_size) * dx, self.height / 2 + (1 - self.minute_ticks_size) * dy)

		self.drawer.ctx.stroke()
		self.drawer.set_source_rgb(self.seconds_hand_color)

		if self.seconds_hand_length > 0:
			self.drawer.ctx.move_to(self.width / 2, self.height / 2)
			self.drawer.ctx.line_to(
				self.width / 2 + math.sin(now.second * math.pi / 30) * self.seconds_hand_length * (self.length / 2 - self.padding),
				self.height / 2 - math.cos(now.second * math.pi / 30) * self.seconds_hand_length * (self.length / 2 - self.padding)
			)

		self.drawer.ctx.stroke()

		self.drawer.draw(offsetx=self.offsetx, offsety=self.offsety, width=self.width, height=self.height)


class VGroupBox(base._Widget):
	orientations = base.ORIENTATION_VERTICAL
	defaults = [
		('gap', 2, "size of gap between groups"),
		('bg_urgent', '#ff7f00', "color of groups with urgent windows"),
		('bg_normal', '#007fff', "color of regular groups"),
		('bg_empty', '#001fbf', "color of groups without windows"),
		('ol_curr', '#bfbfbf', "color of the outline of the currently-displayed group"),
		('ol_other', '#5f5f5f', "color of the outline of groups currently displayed on other screens"),
		('bg_overrides', {}, "dict that maps group names to tuples of (normal color, empty color)"),
	]

	def __init__(self, **config):
		base._Widget.__init__(self, bar.CALCULATED, **config)
		self.add_defaults(VGroupBox.defaults)
		self._prev_height = None

	def calculate_length(self):
		return len(self.qtile.groups)*(self.width-self.gap) + self.gap

	def _configure(self, qtile, bar):
		super()._configure(qtile, bar)
		self.num_groups = len(self.qtile.groups)
		hook.subscribe.addgroup(self.hook_response)
		hook.subscribe.setgroup(self.hook_response)
		hook.subscribe.delgroup(self.hook_response)
		#hook.subscribe.changegroup(self.hook_response)  # TODO: gets called when a group's label changes
		hook.subscribe.client_managed(self.hook_response)
		hook.subscribe.client_urgent_hint_changed(self.hook_response)
		hook.subscribe.client_killed(self.hook_response)

	def hook_response(self, *args, **kwargs):
		self.draw()

	def button_press(self, x, y, button):
		super().button_press(x, y, button)
		if button == 1:
			self.bar.screen.set_group(self.qtile.groups[int(len(self.qtile.groups) * y / self.height)], warp=False)

	def draw(self):
		if self._prev_height is None: self._prev_height = self.height
		elif self._prev_height != self.height:
			self._prev_height = self.height
			return self.bar.draw()
		self.drawer.clear(self.background or self.bar.background)
		for i, group in enumerate(self.qtile.groups):
			if group.screen:
				self.drawer.set_source_rgb(self.ol_curr if group.screen is self.bar.screen else self.ol_other)
				self.drawer.fillrect(0, i * (self.width-self.gap), self.width, self.width)
			self.drawer.set_source_rgb(self.bg_urgent if any(win.urgent for win in group.windows) else self.bg_overrides.get(group.name, (self.bg_normal, self.bg_empty))[1 if len(group.windows) == 0 else 0])
			self.drawer.fillrect(self.gap, i*(self.width-self.gap) + self.gap, self.width - 2*self.gap, self.width - 2*self.gap)
			# TODO: draw the group's label
		self.drawer.draw(offsetx=self.offsetx, offsety=self.offsety, width=self.width, height=self.height)


class BetterBattery(base._TextBox, AsyncMixin):
	"""A widget that displays your laptop's battery charge and can warn you when it's too high or too low.

	Requires psutil.
	"""

	defaults = [
		('update_interval', 15, "update interval in seconds"),
		('format_widget', "{percent:.0f}%", "format text to display in widget"),
		('format_notif', "", "format text to display in notification"),
		('critical_percent', 5, "percentage (0–100) where charge is considered critical"),
		('low_percent', 30, "percentage (0–100) where charge is considered low"),
		('high_percent', 70, "percentage (0–100) where charge is considered high"),
		('foreground_low', '#ff7f00', "font color to use when charge is low"),
		('foreground_high', '#007fff', "font color to use when charge is high"),
		('hibernate_critical', True, "whether to hibernate (suspend-to-disk) when charge is critical"),
		('notify_low', True, "whether to send a DBus notification when charge is low"),
		('notify_high', True, "whether to send a DBus notification when charge is high"),
	]

	def __init__(self, **config):
		base._TextBox.__init__(self, **config)
		AsyncMixin.__init__(self)
		self.add_defaults(BetterBattery.defaults)
		self._fg = None
		self.notif_id_low = 0
		self.notif_low_shown = False
		self.was_already_high = False

	def timer_setup(self):
		self.timeout_add_async(0, self.update_async())

	async def update_async(self):
		# TODO: ditch psutil, do async file I/O on /sys/class/battery/…
		if self._fg is None: self._fg = self.foreground
		res = psutil.sensors_battery()
		if res.percent <= self.critical_percent and not res.power_plugged and self.hibernate_critical:
			os.system('systemctl hibernate')
		elif res.percent <= self.low_percent and not res.power_plugged:
			self.foreground = self.foreground_low
			self.was_already_high = False
			if self.notify_low:
				self.notif_id_low = await mydbus.notify_async("battery low", self.format_notif.format(**res._asdict()), replaces_id=self.notif_id_low, hints={'urgency': Variant('y', 2), 'value': Variant('u', round(res.percent))})
				self.notif_low_shown = True
		elif res.percent >= self.high_percent and res.power_plugged:
			self.foreground = self.foreground_high
			if not self.was_already_high:
				self.was_already_high = True
				if self.notify_high: await mydbus.notify_async("battery high", self.format_notif.format(**res._asdict()), hints={'value': Variant('u', round(res.percent))})
		else:
			self.foreground = self._fg
			self.was_already_high = False
			if self.notif_low_shown:
				await mydbus.close_notification_async(self.notif_id_low)
				self.notif_low_shown = False
		self.text = self.format_widget.format(**res._asdict())
		self.draw()
		self.timeout_add_async(self.update_interval, self.update_async())


class MprisAllPlayersController(base._Widget, AsyncMixin):
	defaults = [
		('single_player', True, "pause all other players when one starts playing"),
		('notify', True, "send a notification when a song/video starts playing"),
		('notify_on_resume', False, "also send a notification when a song/video resumes (from being paused)"),
		('notif_format_title', "{xesam->title}", "format text for the notification title"),
		('notif_format_body', "by {xesam->artist}\nnow playing in {widget->playername}", "format text for the notification body"),
		('notif_appname_is_playername', False, "use the player's display name as the application name in the notification"),
		('metadata_fallback_value', "???", "default value to use for non-present metadata"),
	]

	class _Player:
		def __init__(self, name, mpri, mpri_player):
			self.name = name
			self.mpri = mpri
			self.mpri_player = mpri_player
			self.playback_status = None

	def __init__(self, **config):
		base._Widget.__init__(self, bar.CALCULATED, **config)
		AsyncMixin.__init__(self)
		self.add_defaults(MprisAllPlayersController.defaults)
		self._players = {}
		self._recent_players = []

	def calculate_length(self):
		return self.bar.size

	async def _config_async(self):
		self._bus = await MessageBus().connect()
		is_dbus = await self._bus.introspect('org.freedesktop.DBus', '/org/freedesktop/DBus')
		if_dbus = self._bus.get_proxy_object('org.freedesktop.DBus', '/org/freedesktop/DBus', is_dbus).get_interface('org.freedesktop.DBus')
		await asyncio.gather(*(self._add_player(bus_name) for bus_name in await if_dbus.call_list_names() if bus_name.startswith('org.mpris.MediaPlayer2.')))
		if_dbus.on_name_owner_changed(self._name_owner_changed)
		if self.notify:
			is_notif = await self._bus.introspect('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
			self._if_notif = self._bus.get_proxy_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications', is_notif).get_interface('org.freedesktop.Notifications')

	def _name_owner_changed(self, name, old_owner, new_owner):
		logger.debug("name owner changed: {}: {} -> {}".format(name, old_owner, new_owner))
		if name.startswith('org.mpris.MediaPlayer2.'):
			if old_owner == '':
				self.timeout_add_async(0, self._add_player(name))
			elif new_owner == '':
				if name in self._players:
					# TODO: stop listening to property change event
					self._recent_players.remove(self._players[name])
					del self._players[name]
					self.draw()

	async def _add_player(self, bus_name):
		introspection = await self._bus.introspect(bus_name, '/org/mpris/MediaPlayer2')
		obj = self._bus.get_proxy_object(bus_name, '/org/mpris/MediaPlayer2', introspection)

		mpri = obj.get_interface('org.mpris.MediaPlayer2')
		mpri_player = obj.get_interface('org.mpris.MediaPlayer2.Player')

		displayname = await mpri.get_identity()
		status = await mpri_player.get_playback_status()

		player = MprisAllPlayersController._Player(displayname, mpri, mpri_player)
		player.playback_status = status
		self._players[bus_name] = player
		self._recent_players.insert(0, player)
		logger.info("managing {} ({})".format(displayname, bus_name))

		properties = obj.get_interface('org.freedesktop.DBus.Properties')

		properties.on_properties_changed(functools.partial(self._properties_changed, bus_name))

	def _properties_changed(self, bus_name, interface_name, changed_properties, invalidated_properties):
		logger.debug("property change of {} (on {})".format(interface_name, bus_name))
		if interface_name == 'org.mpris.MediaPlayer2.Player':
			player = self._players[bus_name]
			if 'PlaybackStatus' in changed_properties:
				status = changed_properties['PlaybackStatus'].value
				logger.info("{} changed from {} to {}".format(player.name, player.playback_status, status))
				if status == 'Playing':
					if self._recent_players[-1] is not player:
						self._recent_players.remove(player)
						self._recent_players.append(player)
					if self.single_player:
						for other in self._players.values():
							if other is not player:
								self.timeout_add_async(0, other.mpri_player.call_pause())
					if self.notify and not (player.playback_status == 'Paused' and not self.notify_on_resume):
						self.timeout_add_async(0, self._notify_about(player))
				elif status == 'Paused':
					if len(self._recent_players) > 1:
						self._recent_players.remove(player)
						for (i, other) in self._recent_players:
							if other.playback_status == 'Playing':
								self._recent_players.insert(i, player)
								break
						else: self._recent_players.append(player)
				elif status == 'Stopped':
					if len(self._recent_players) > 1:
						self._recent_players.remove(player)
						for (i, other) in self._recent_players:
							if other.playback_status == 'Paused' or other.playback_status == 'Playing':
								self._recent_players.insert(i, player)
								break
						else: self._recent_players.append(player)
				player.playback_status = changed_properties['PlaybackStatus'].value
				self.draw()
			elif 'Metadata' in changed_properties:
				logger.info("{} metadata changed".format(player.name))
				if self.notify and (player.playback_status == 'Playing' or player.playback_status == 'Paused'): self.timeout_add_async(0, self._notify_with(changed_properties['Metadata'].value, player.name))

	async def _notify_about(self, player):
		await self._notify_with((await player.mpri_player.get_metadata()), player.name)

	async def _notify_with(self, metadata, displayname):
		metadata = defaultdict(lambda: self.metadata_fallback_value, [(key.replace(':', '->'), variant.value) for (key, variant) in metadata.items()] + [('widget->playername', displayname)])
		await self._if_notif.call_notify(
			displayname if self.notif_appname_is_playername else "qtile",
			0,  # replaces_id
			'',  # TODO: icon_name
			self.notif_format_title.format_map(metadata),
			self.notif_format_body.format_map(metadata),
			[],  # TODO: actions
			{},  # hints
			-1,  # expire_timeout
		)

	def draw(self):
		self.drawer.clear(self.background or self.bar.background)
		self.drawer.set_source_rgb(self.foreground)
		if len(self._recent_players) == 0:
			self.drawer.ctx.new_sub_path()
			self.drawer.ctx.arc(self.width / 6, self.height * 5/6, self.length / 6, 0, 2 * math.pi)
			self.drawer.ctx.fill()

			self.drawer.ctx.new_sub_path()
			self.drawer.ctx.arc(self.width * 5/6, self.height * 5/6, self.length / 6, 0, 2 * math.pi)
			self.drawer.ctx.fill()

			self.drawer.ctx.new_sub_path()
			self.drawer.ctx.move_to(self.width/3 - 1, 0)
			self.drawer.ctx.line_to(self.width, 0)
			self.drawer.ctx.line_to(self.width, self.height * 5/6)
			self.drawer.ctx.line_to(self.width - 1, self.height * 5/6)
			self.drawer.ctx.line_to(self.width - 1, self.height / 4)
			self.drawer.ctx.line_to(self.width / 3, self.height / 4)
			self.drawer.ctx.line_to(self.width / 3, self.height * 5/6)
			self.drawer.ctx.line_to(self.width/3 - 1, self.height * 5/6)
			self.drawer.ctx.close_path()
			self.drawer.ctx.fill()
		elif self._recent_players[-1].playback_status == 'Playing':
			self.drawer.fillrect(self.width * 1.5/12, 0, self.width / 4, self.height)
			self.drawer.fillrect(self.width * 7.5/12, 0, self.width / 4, self.height)
		else:
			self.drawer.ctx.move_to(0, 0)
			self.drawer.ctx.line_to(self.width, self.height / 2)
			self.drawer.ctx.line_to(0, self.height)
			self.drawer.ctx.close_path()
			self.drawer.ctx.fill()
		self.drawer.draw(offsetx=self.offsetx, offsety=self.offsety, width=self.width, height=self.height)
