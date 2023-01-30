import asyncio
import random

from dbus_next.aio import MessageBus


_bus = None

async def _interface(bus_name, path, object_name):
	global _bus
	if _bus is None: _bus = await MessageBus().connect()
	introspection = await _bus.introspect(bus_name, path)
	return _bus.get_proxy_object(bus_name, path, introspection).get_interface(object_name)


_interface_notif = None

async def notify_async(summary, body="", /, *, app_name="qtile", replaces_id=0, app_icon='', actions={}, hints={}, expire_timeout=-1):
	global _interface_notif
	if _interface_notif is None: _interface_notif = await _interface('org.freedesktop.Notifications', '/org/freedesktop/Notifications', 'org.freedesktop.Notifications')
	return await _interface_notif.call_notify(app_name, replaces_id, app_icon, summary, body, [(identifier, actions[identifier]) for identifier in actions], hints, expire_timeout)

async def close_notification_async(id):
	global _interface_notif
	if _interface_notif is None: _interface_notif = await _interface('org.freedesktop.Notifications', '/org/freedesktop/Notifications', 'org.freedesktop.Notifications')
	await _interface_notif.call_close_notification(id)


_tasks = set()

def notify(summary, body="", /, *, app_name="qtile", replaces_id=0, app_icon='', actions={}, hints={}, expire_timeout=-1):
	if replaces_id == 0: replaces_id = random.getrandbits(31) # doing the server's job
	task = asyncio.create_task(notify_async(summary, body, app_name=app_name, replaces_id=replaces_id, app_icon=app_icon, actions=actions, hints=hints, expire_timeout=expire_timeout))
	_tasks.add(task)
	task.add_done_callback(_tasks.discard)
	return replaces_id

def close_notification(id):
	task = asyncio.create_task(close_notification_async(id))
	_tasks.add(task)
	task.add_done_callback(_tasks.discard)