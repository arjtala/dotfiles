(require-package 'monokai-theme)
(require-package 'leuven-theme)
(require-package 'badwolf-theme)
(require-package 'zenburn-theme)
(require-package 'solarized-theme)

;; Function for cleaning switching themes
(defun switch-theme (theme)
  ;; This interactive call is taken from `load-theme'
  (interactive
   (list
    (intern (completing-read "Load custom theme: "
                             (mapcar 'symbol-name
                                     (custom-available-themes))))))
  (mapcar #'disable-theme custom-enabled-themes)
  ;; (spaceline-spacemacs-theme)
  (load-theme theme t))
