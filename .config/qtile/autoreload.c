#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/inotify.h>
#include <sys/wait.h>
#include <unistd.h>


int fd = -1, wd = -1;

void cleanup(void) {
	if (fd != -1 && wd != -1) {
		if (inotify_rm_watch(fd, wd) == -1) perror("inotify_rm_watch");
		else wd = -1;
	}
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
	wd = inotify_add_watch(fd, ".config/qtile/", IN_CLOSE_WRITE|IN_MOVED_TO|IN_ONLYDIR|IN_MASK_CREATE);
	if (wd == -1) {
		if (errno == EEXIST) return EXIT_SUCCESS;  // we are already watching, and being called again, so just quit
		perror("inotify_add_watch: \".config/qtile/\"");
		return EXIT_FAILURE;
	}
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
			if (event->wd == -1 && event->mask & IN_Q_OVERFLOW) {
				fputs("the inotify event queue overflowed\n", stderr);
				return EXIT_FAILURE;
			}
			if (event->mask & IN_IGNORED) {  // watch is gone, be done
				wd = -1;
				return EXIT_SUCCESS;
			}
			if (event->len > 0) {
				if (strcmp(event->name, "autoreload") == 0) {  // the compiled binary of this program changed: execlp self (no need to reload qtile)
					execlp("autoreload", ".config/qtile/autoreload", (char *)NULL);
					perror("execlp");
					return EXIT_FAILURE;
				} else if (strcmp(event->name, "autoreload.c") != 0) {  // ignore changes to this file
					pid_t pid = fork();
					int wstatus;
					if (pid == -1) perror("fork");  // but this isn' fatal, we can try again next time something is changed
					else if (pid == 0) {
						execlp("qtile", "qtile", "cmd-obj", "-o", "root", "-f", "reload_config", (char *)NULL);
						// if this returns, an error occured
						// try again next time here as well
						// but since we forked, this one must end
						perror("execlp");
						return EXIT_FAILURE;
					} else if (waitpid(pid, &wstatus, 0) == -1) perror("waitpid");  // but don't exit
					else if (!WIFEXITED(wstatus) || WEXITSTATUS(wstatus) != 0) fputs("reloading config failed in some way\n", stderr);
				}
			}
			off += sizeof (struct inotify_event) + event->len;
		}
	}
	return EXIT_SUCCESS;
}
