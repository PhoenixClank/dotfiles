#!/usr/bin/zsh

case $1 in
	down)
		ws=$(swaymsg -r -t get_workspaces | jq -r '[.[index(.[] | select(.focused))+1 :].[] | select(.visible | not)][0].num')
		if [[ $ws == "null" ]]; then
			ws=$(date +%s)
		fi
		swaymsg "move to workspace number $ws; workspace number $ws"
		;;
	up)
		if ws=$(swaymsg -r -t get_workspaces | jq -r -e '[.[: index(.[] | select(.focused))].[] | select(.visible | not)][-1].num'); then
			swaymsg "move to workspace number $ws; workspace number $ws"
		fi
		;;
	*)
		exit 1
esac
