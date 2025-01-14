colors mine

set mouse=

set number
set numberwidth=1

set cursorline

set nowrap
set linebreak
set whichwrap=b,s,<,>,[,]

set fo-=r

set tabstop=4
set shiftwidth=4
set noexpandtab
set nosmarttab

set scrolloff=5
set sidescroll=0
set sidescrolloff=10

"set selectmode=key
"set keymodel=startsel,stopsel

set foldmethod=marker

if has("autocmd")
	augroup skel
		autocmd BufNewFile *.xhtml 0r ~/templates/skel.xhtml
	augroup END
endif
