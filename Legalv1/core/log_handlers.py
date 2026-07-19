"""
Multi-process-safe rotating log handlers.

The stdlib ``TimedRotatingFileHandler`` is NOT safe when several processes
(8 gunicorn workers + multiple celery workers) write to the same file: each
process holds its own file descriptor and its own rollover timer, so at
midnight only one process renames the file while the others keep appending to
the now-renamed inode. The result is yesterday's-dated file growing with
today's data and an almost-empty active file.

``concurrent_log_handler.ConcurrentTimedRotatingFileHandler`` fixes that with
cross-process file locking. This subclass adds the desired archive naming:
the date is placed *before* the ``.log`` extension, e.g.::

    django.log              <- active file
    django.2026-06-27.log   <- rolled archive for 2026-06-27

The default handler would instead produce ``django.log.2026-06-27`` (date at
the very end). Because we change the archive name, we also override
``getFilesToDelete`` so ``backupCount`` retention keeps working with the new
pattern.
"""
import os
import time

from concurrent_log_handler import ConcurrentTimedRotatingFileHandler


class MiddleDateTimedRotatingFileHandler(ConcurrentTimedRotatingFileHandler):
    """Multi-process-safe timed handler that names archives ``<stem>.<date><ext>``."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # rotation_filename() calls self.namer() if it is set.
        self.namer = self._middle_date_namer

    def _parts(self):
        """Return (dir, stem, ext) for the active file, e.g. ('logs', 'django', '.log')."""
        dir_name, base_name = os.path.split(self.baseFilename)
        stem, ext = os.path.splitext(base_name)
        return dir_name, stem, ext

    def _middle_date_namer(self, default_name):
        """Transform 'logs/django.log.2026-06-27' -> 'logs/django.2026-06-27.log'.

        ``default_name`` is ``baseFilename + '.' + <date-suffix>`` and may carry a
        trailing ``.N`` collision counter and/or a ``.gz`` extension; both are
        preserved after the date so the date stays the sortable key.
        """
        dir_name, stem, ext = self._parts()
        base_name = os.path.basename(self.baseFilename)
        fname = os.path.basename(default_name)
        # Everything the default handler appended after "<base_name>."
        suffix_part = fname[len(base_name) + 1:]
        return os.path.join(dir_name, f"{stem}.{suffix_part}{ext}")

    def getFilesToDelete(self):
        """Find rolled archives matching ``<stem>.<date><ext>[.N][.gz]`` for retention."""
        dir_name, stem, ext = self._parts()
        active = os.path.basename(self.baseFilename)
        prefix = stem + "."
        gzip_ext = ".gz" if self.clh.use_gzip else ""

        candidates = []
        for fname in os.listdir(dir_name):
            if fname == active or not fname.startswith(prefix):
                continue
            name = fname[:-len(gzip_ext)] if gzip_ext and fname.endswith(gzip_ext) else fname
            if not name.endswith(ext):
                continue
            middle = name[len(prefix):-len(ext)]  # "2026-06-27" or "2026-06-27.1"
            date_token = middle.split(".", 1)[0]
            try:
                time.strptime(date_token, self.suffix)
            except (ValueError, TypeError):
                continue
            candidates.append((date_token, fname))

        if len(candidates) <= self.backupCount:
            return []
        candidates.sort()
        num_to_delete = len(candidates) - self.backupCount
        return [os.path.join(dir_name, f) for _, f in candidates[:num_to_delete]]
