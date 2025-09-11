" auto-close XML paired delimiters

if exists("b:loaded_xml_autodelim")
	finish
endif
let b:loaded_xml_autodelim = 1

inoremap <buffer> <lt> ><Left>/<Left><lt>
inoremap <buffer> <expr> / <SID>Slash()
inoremap <buffer> <expr> ? <Sid>Question()
inoremap <buffer> <expr> ! <SID>Bang()
inoremap <buffer> <expr> - <SID>Hyphen()
inoremap <buffer> <expr> > <SID>GreaterThan()

if !exists("*s:Slash")
	function s:Slash()
		let l:line = getline(".")
		let l:col = col(".")
		if l:line[l:col-1 : l:col] == "/>"
			return "\<Right>"
		endif
		return "/"
	endfunction
endif

if !exists("*s:Question")
	function s:Question()
		let l:col = col(".")
		if getline(".")[l:col-2 : l:col] == "</>"
			return "\<Del>??\<Left>"
		endif
		return "?"
	endfunction
endif

if !exists("*s:Bang")
	function s:Bang()
		let l:col = col(".")
		if getline(".")[l:col-2 : l:col] == "</>"
			return "\<Del>!"
		endif
		return "!"
	endfunction
endif

if !exists("*s:Hyphen")
	function s:Hyphen()
		let l:col = col(".")
		if getline(".")[l:col-3 : l:col-1] == "<!>"
			return "----\<Left>\<Left>"
		endif
		return "-"
	endfunction
endif

if !exists("*s:GreaterThan")
	function s:GreaterThan()
		let l:line = getline(".")
		let l:col = col(".")
		if l:line[l:col - 1] == ">"
			return "\<Right>"
		elseif l:line[l:col-1 : l:col] == "/>"
			let l:i = l:col - 1
			let l:j = l:i - 1
			while l:line[l:i] != "<"
				if l:line[l:i] == " " | let l:j = l:i - 1 | endif
				let l:i -= 1
				if l:i == 0 | break | endif
			endwhile
			let l:tag = l:line[l:i+1 : l:j]
			let l:back = "\<Left>\<Left>"
			for l:_ in l:tag | let l:back ..= "\<Left>" | endfor
			return "><\<Right>" .. l:tag .. l:back
		endif
		return ">"
	endfunction
endif
