run_further=true
graphical_session=true

# handle backups first and foremost
if $run_further ; then
	# TODO: what if, after a fresh install, .backup_time is missing?
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

# check Arch Linux News, which also tells us whether we're connected to the internet
online=false
if $run_further ; then
	./news_nag.py
	case $? in
		0) # exited normally
			online=true
			;;
		1) # dismissed
			online=true
			run_further=false
			;;
		2) # read through, but go to shell
			online=true
			graphical_session=false
			;;
		3) # no internet connection
			online=false
			;;
	esac
fi

# nag for system upgrades …
if $run_further && $online ; then
	# TODO: what if, after a fresh install, /etc/syu_time is missing?
	syu_age=$(( ($(date "+%s") - $(date -r /etc/syu_time "+%s")) / 60 / 60 / 24 ))
	if (( $syu_age >= 5 )) ; then  # … every 5 days
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

# download Lenov's pictures …
if $run_further ; then
	u=$(date "+%u")
	if (( $u == 2 || $u == 6 )) ; then  # … every Tuesday and Saturday
		[[ ! -e .lenov_state ]] && $online && ./lenov_load && touch .lenov_state
	else
		rm -f .lenov_state
	fi
fi

# finally, start graphical session
if $graphical_session ; then
	mv -f .local/share/qtile/qtile.log .local/share/qtile/qtile.log.prev
	mv -f .local/share/qtile/qtile.run .local/share/qtile/qtile.run.prev
	qtile start -b wayland > .local/share/qtile/qtile.run 2>&1
fi
