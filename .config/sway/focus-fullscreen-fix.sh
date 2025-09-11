#!/bin/sh

swaymsg -m -t subscribe '["window"]' | jq -r --unbuffered 'select(.change == "new").container.id' | while read curr; do
	if [ $(swaymsg -r -t get_tree | jq '.. | select(.focused?).fullscreen_mode') = 1 ]; then
		swaymsg "[con_id=$curr] focus"
	fi
done
