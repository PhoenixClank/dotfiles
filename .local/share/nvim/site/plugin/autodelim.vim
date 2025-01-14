" auto-close paired delimiters

if exists("g:loaded_autodelim")
	finish
endif
let g:loaded_autodelim = 1

inoremap ( ()<Left>
inoremap [ []<Left>
inoremap { {}<Left>

inoremap <expr> } <SID>MaybeSkip("}")
inoremap <expr> ] <SID>MaybeSkip("]")
inoremap <expr> ) <SID>MaybeSkip(")")

inoremap <expr> " <SID>DoubleQuote()

inoremap <expr> <BS> <SID>Remove()

inoremap <expr> <Enter> <SID>LineBreak()


function s:MaybeSkip(right)
	if getline(".")[col(".")-1] == a:right
		return "\<Right>"
	endif
	return a:right
endfunction

function s:DoubleQuote()
	let l:line = getline(".")
	let l:col = col(".")
	if l:line[l:col-2] == "\\"
		return "\""
	elseif l:line[l:col-1] == "\""
		if l:line[l:col-2] == "\""
			return "\"\"\"\"\<Left>\<Left>"
		endif
		return "\<Right>"
	endif
	return "\"\"\<Left>"
endfunction

function s:Remove()
	let l:line = getline(".")
	let l:col = col(".")
	if l:line[l:col-2 : l:col-1] == "()" || l:line[l:col-2 : l:col-1] == "[]" || l:line[l:col-2 : l:col-1] == "{}"
		return "\<Del>\<BS>"
	elseif l:line[l:col-3 : l:col-2] == "()" || l:line[l:col-3 : l:col-2] == "[]" || l:line[l:col-3 : l:col-2] == "{}"
		return "\<BS>\<BS>"
	endif
	return "\<BS>"
endfunction

function s:LineBreak()
	let l:line = getline(".")
	let l:col = col(".")
	if l:line[l:col-2 : l:col-1] == "()" || l:line[l:col-2 : l:col-1] == "[]" || l:line[l:col-2 : l:col-1] == "{}"
		return "\<Enter>\<Tab>\<Enter>\<Up>\<Right>"
	endif
	return "\<Enter>"
endfunction
