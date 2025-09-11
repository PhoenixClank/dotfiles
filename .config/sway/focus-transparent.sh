#!/bin/sh

prev="$(swaymsg -r -t get_seats | jq -r '.[0].focus')"
swaymsg -m -t subscribe '["window"]' | jq -r --unbuffered 'select(.change == "focus").container.id' | while read curr; do
	swaymsg "[con_id=$prev] opacity .75; [con_id=$curr] opacity 1"
	prev="$curr"
done
