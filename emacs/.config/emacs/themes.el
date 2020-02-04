(require-package 'monokai-theme)
(require-package 'leuven-theme)
(require-package 'badwolf-theme)
(require-package 'zenburn-theme)
(require-package 'solarized-theme)
(require-package 'arc-dark-theme)

(add-to-list 'custom-theme-load-path "~/.config/emacs/themes/")

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

(use-package doom-themes
  :config
  ;; Global settings (defaults)
  (setq doom-themes-enable-bold t    ; if nil, bold is universally disabled
        doom-themes-enable-italic t) ; if nil, italics is universally disabled
  (load-theme 'doom-nord-light t)

  ;; Enable flashing mode-line on errors
  (doom-themes-visual-bell-config)
  
  ;; Enable custom neotree theme (all-the-icons must be installed!)
  (doom-themes-neotree-config)
  ;; this isn't necessary, because 'simple is the default
  (setq doom-neotree-file-icons 'simple)
  ;; or for treemacs users
  ;; (setq doom-themes-treemacs-theme "doom-colors") ; use the colorful treemacs theme
  ;; (doom-themes-treemacs-config)
  
  ;; Corrects (and improves) org-mode's native fontification.
  (doom-themes-org-config))
