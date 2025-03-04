#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/inotify.h>
#include <sys/wait.h>
#include <unistd.h>

#include <expat.h>


int fd = -1;
int wd_rc = -1, wd_theme = -1;
int f = -1;
XML_Parser p = NULL;
char *theme_name = NULL;
size_t theme_name_len = 0;
size_t theme_name_capac = 0;


void cleanup(void) {
	if (theme_name) {
		free(theme_name);
		theme_name = NULL;
		theme_name_len = 0;
		theme_name_capac = 0;
	}
	if (p) {
		XML_ParserFree(p);
		p = NULL;
	}
	if (f != -1) {
		if (close(f) != 0) perror("close");
		else f = -1;
	}
	if (fd != -1) {
		if (wd_rc != -1) {
			if (inotify_rm_watch(fd, wd_rc) == -1) perror("inotify_rm_watch");
			else wd_rc = -1;
		}
		if (wd_theme != -1) {
			if (inotify_rm_watch(fd, wd_theme) == -1) perror("inotify_rm_watch");
			else wd_theme = -1;
		}
	}
}


int own_error = 0;

// XML parsing {{{
unsigned stack = 0, skip = 0;

void XMLCALL starttag(void *user_data, const char *name, const char **attrs) {
	if (skip > 0) ++skip;
	else switch (stack) {
		case 0:
			if (strcmp(name, "openbox_config") == 0) stack = 1;
			else skip = 1;
			break;
		case 1:
			if (strcmp(name, "theme") == 0) stack = 2;
			else skip = 1;
			break;
		case 2:
			if (strcmp(name, "name") == 0) {
				stack = 3;
				// theme name just started: reset buffer
				if (theme_name) {
					free(theme_name);
					theme_name = NULL;
					theme_name_capac = 0;
					theme_name_len = 0;
				}
			} else skip = 1;
			break;
	}
}

void XMLCALL endtag(void *user_data, const XML_Char *name) {
	if (skip > 0) --skip;
	else switch (stack) { 
		case 3:
			if (strcmp(name, "name") == 0) {
				stack = 2;
				// add terminating null character
				if (theme_name_len == theme_name_capac) {
					theme_name = realloc(theme_name, theme_name_capac + 1);
					++theme_name_capac;
				}
				theme_name[theme_name_len] = '\0';
			}
			break;
		case 2:
			if (strcmp(name, "theme") == 0) stack = 1;
			break;
		case 1:
			if (strcmp(name, "openbox_config") == 0) stack = 0;
			break;
	}
}

void XMLCALL chardata(void *user_data, const char *s, int len) {
	if (len < 0) return;
	if (stack != 3 || skip > 0) return;
	if (!theme_name) {
		theme_name = malloc(NAME_MAX + 1);
		if (!theme_name) {
			perror("malloc");
			own_error = 1;
			return;
		}
		theme_name_capac = NAME_MAX + 1;
	}
	// as this is a void function I'm not sure how I should do error handling
	// let's just let the program segfault
	if (theme_name_len + len >= theme_name_capac) {
		theme_name = realloc(theme_name, theme_name_capac * 2);
		if (!theme_name) {
			perror("realloc");
			own_error = 1;
			return;
		}
		theme_name_capac *= 2;
	}
	memcpy(theme_name, s, len);
	theme_name_len += len;
}
// }}}

void parse_rc(void) {
	f = open(".config/openbox/rc.xml", O_RDONLY);
	if (f == -1) {
		perror("open: .config/openbox/rc.xml");
		own_error = 1;
		return;
	}
	p = XML_ParserCreate(NULL);
	XML_SetElementHandler(p, starttag, endtag);
	XML_SetCharacterDataHandler(p, chardata);
	while (1) {
		void *buf = XML_GetBuffer(p, 4096);
		if (!buf) {
			fputs("couldn’t get a buffer from expat\n", stderr);
			own_error = 1;
			return;
		}
		ssize_t r = read(f, buf, 4096);
		if (r < 0) {
			perror("read: .config/openbox/rc.xml");
			own_error = 1;
			return;
		}
		XML_ParseBuffer(p, r, r == 0);
		if (own_error) return;
		if (r == 0) break;
	}
	XML_ParserFree(p);
	p = NULL;
	if (close(f) != 0) perror("close");
	else f = -1;
}

void watch_theme(void) {
	char pathname[theme_name_len + 32];
	strcpy(pathname, ".local/share/themes/");
	strcat(pathname, theme_name);
	strcat(pathname, "/openbox-3/");
	wd_theme = inotify_add_watch(fd, pathname, IN_CLOSE_WRITE|IN_MOVED_TO|IN_ONLYDIR);
	if (wd_theme == -1) {
		if (errno != ENOENT) {
			fprintf(stderr, "inotify_add_watch: %s: ", pathname);
			perror(NULL);
			own_error = 1;
			return;
		}
		memcpy(pathname + 2, "/usr", 4);
		wd_theme = inotify_add_watch(fd, pathname + 2, IN_CLOSE_WRITE|IN_MOVED_TO|IN_ONLYDIR);
		if (wd_theme == -1) {
			fprintf(stderr, "inotify_add_watch: %s: ", pathname + 2);
			perror(NULL);
			own_error = 1;
			return;
		}
	}
}

int fork_and_exec(const char *file, char *const argv[]) {
	pid_t pid = fork();
	int wstatus;
	if (pid == -1) perror("fork");  // but this isn' fatal, we can try again next time something is changed
	else if (pid == 0) {
		execvp(file, argv);
		// if this returns, an error occured
		// try again next time here as well
		// but since we forked, this one must end
		perror("execvp");
		return 0;
	} else if (waitpid(pid, &wstatus, 0) == -1) perror("waitpid");  // but don't exit
	else if (!WIFEXITED(wstatus) || WEXITSTATUS(wstatus) != 0) fputs("reloading config failed in some way\n", stderr);
	return 1;
}


int main(void) {
	if (atexit(cleanup) != 0) {
		perror("atexit");
		return EXIT_FAILURE;
	}
	fd = inotify_init();
	if (fd == -1) {
		perror("inotify_init");
		return EXIT_FAILURE;
	}
	wd_rc = inotify_add_watch(fd, ".config/openbox/", IN_CLOSE_WRITE|IN_MOVED_TO|IN_ONLYDIR);
	if (wd_rc == -1) {
		perror("inotify_add_watch: .config/openbox/");
		return EXIT_FAILURE;
	}

	parse_rc();
	if (own_error) return EXIT_FAILURE;
	watch_theme();
	if (own_error) return EXIT_FAILURE;
	
	char buf[sizeof (struct inotify_event) + NAME_MAX + 1];
	while (1) {
		const ssize_t r = read(fd, buf, sizeof (buf));
		if (r == -1) {
			perror("read");
			return EXIT_FAILURE;
		}
		size_t off = 0;
		while (off + sizeof (struct inotify_event) <= r) {
			struct inotify_event *event = (struct inotify_event *)(buf + off);

			if (event->mask & IN_Q_OVERFLOW) {
				fputs("the inotify event queue overflowed\n", stderr);
				return EXIT_FAILURE;
			} else if (event->mask & IN_IGNORED) {  // watch is gone, acquire a new one
				if (event->wd == wd_rc) {
					wd_rc = inotify_add_watch(fd, ".config/openbox/", IN_CLOSE_WRITE|IN_MOVED_TO|IN_ONLYDIR);
					if (wd_rc == -1) {
						perror("inotify_add_watch: .config/openbox/");
						return EXIT_FAILURE;
					}
				} else if (event->wd == wd_theme) {
					watch_theme();
					if (own_error) return EXIT_FAILURE;
				}
			} else if (event->wd == wd_rc && strcmp(event->name, "autoreload") == 0) {  // the compiled binary of this program changed: execlp self (no need to reload anything)
				execlp(".config/openbox/autoreload", ".config/openbox/autoreload", (char *)NULL);
				perror("execlp");
				return EXIT_FAILURE;
			} else if (event->wd == wd_rc && strcmp(event->name, "autostart") == 0) {
				char *const argv[] = {"sh", ".config/openbox/autostart", NULL};
				if (!fork_and_exec("sh", argv)) return EXIT_FAILURE;
			} else if (event->wd == wd_theme || strcmp(event->name, "autoreload.c") != 0) {  // ignore changes to this file
				if (event->wd == wd_rc && strcmp(event->name, "rc.xml") == 0) {
					if (inotify_rm_watch(fd, wd_theme) == -1) {
						perror("inotify_rm_watch");
						return EXIT_FAILURE;
					} else wd_theme = -1;
					parse_rc();
					if (own_error) return EXIT_FAILURE;
					watch_theme();
					if (own_error) return EXIT_FAILURE;
				}
				char *const argv[] = {"openbox", "--reconfigure", NULL};
				if (!fork_and_exec("openbox", argv)) return EXIT_FAILURE;
			}

			off += sizeof (struct inotify_event) + event->len;
		}
	}
	return EXIT_SUCCESS;
}
