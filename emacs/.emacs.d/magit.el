;; Magit
(require-package 'magit)
(require 'magit)

(require-package 'evil-magit)

(require-package 'git-timemachine)

(defun git/init-evil-magit ()
  (interactive)
  (with-eval-after-load 'magit
    (require 'evil-magit)))

(add-hook 'magit-status-mode-hook 'git/init-evil-magit)
