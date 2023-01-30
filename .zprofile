run_further=true
graphical_session=true

if $run_further ; then
	backup_age=$(( ($(date "+%s") - $(date -r .backup_time "+%s")) / 60 / 60 / 24 ))
	if (( $backup_age >= 14 )) ; then
		print "last backup was \e[1m\e[31m$backup_age days\e[39m\e[22m ago"
		vared -p "%B[Enter]: dismiss%b | s: back up now, i: ignore for now | " -c backup_ans
		if [[ -z "$backup_ans" ]] ; then
			run_further=false
		elif [[ "$backup_ans" == "s" ]] ; then
			./backup.sh
		fi
	fi
fi

online=true

if $run_further ; then
	./news_nag.py
	case $? in
		1) # dismissed
			run_further=false
			;;
		2) # read through, but go to shell
			graphical_session=false
			;;
		3) # no internet connection
			online=false
			;;
	esac
fi

if $run_further && $online ; then
	syu_age=$(( ($(date "+%s") - $(date -r .syu_time "+%s")) / 60 / 60 / 24 ))
	if (( $syu_age >= 5 )) ; then
		print "last system upgrade was \e[1m\e[31m$syu_age days\e[39m\e[22m ago"
		vared -p "%B[Enter]: dismiss%b | s: go to shell, i: ignore for now | " -c syu_ans
		if [[ -z "$syu_ans" ]] ; then
			run_further=false
		elif [[ "$syu_ans" == "s" ]] ; then
			run_further=false
			graphical_session=false
		fi
	fi
fi

if $run_further ; then
	if (( $(date "+%d") < 5 )) ; then
		print -n 0 > lenov_state
	elif $online && [[ $(< lenov_state) != 2 ]] ; then
		./lenov_load.py
	fi
fi

if $graphical_session ; then
	mv -f .local/share/qtile/qtile.log .local/share/qtile/qtile.log.prev
	mv -f .local/share/qtile/qtile.run .local/share/qtile/qtile.run.prev
	qtile start -b wayland > .local/share/qtile/qtile.run 2>&1
fi