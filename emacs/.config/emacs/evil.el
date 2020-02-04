;; Evil mode 

(setq evil-want-keybinding nil)
(require-package 'evil)
(setq evil-want-C-u-scroll t)
(require 'evil)
(evil-mode 1)

;; Evil commentary
(require-package 'evil-commentary)
(require 'evil-commentary)
(evil-commentary-mode)

;;Numbers
(require-package 'evil-numbers)
(require 'evil-numbers)

(require-package 'evil-org)
(require 'evil-org)
(add-hook 'org-mode-hook 'evil-org-mode)
(add-hook 'org-mode-hook 'auto-fill-mode)

(global-set-key (kbd "C-x") nil)
(define-key evil-normal-state-map (kbd "C-a") 'evil-numbers/inc-at-pt)
(define-key evil-normal-state-map (kbd "C-x") 'evil-numbers/dec-at-pt)
(define-key evil-normal-state-map (kbd "C-u") 'evil-scroll-up)

;;Leader
(require-package 'evil-leader)
(require 'evil-leader)

(require-package 'evil-magit)
(require 'evil-magit)

(require-package 'evil-matchit)
(require 'evil-matchit)
(global-evil-matchit-mode 1)

(global-evil-leader-mode)
(evil-leader/set-leader "<SPC>")
(evil-leader/set-key "ff" 'helm-find-files)
(evil-leader/set-key "fs" 'helm-find)
(evil-leader/set-key "fr" 'helm-recentf)
(evil-leader/set-key ":" 'helm-M-x)
(evil-leader/set-key "wv" 'evil-window-vsplit)
(evil-leader/set-key "ws" 'evil-window-split)
(evil-leader/set-key "wl" 'evil-window-right)
(evil-leader/set-key "wh" 'evil-window-left)
(evil-leader/set-key "wj" 'evil-window-down)
(evil-leader/set-key "wk" 'evil-window-up)
(evil-leader/set-key "wo" 'delete-other-windows)

(evil-leader/set-key "wwn" 'make-frame)

(evil-leader/set-key "bb" 'helm-buffers-list)
(evil-leader/set-key "bn" 'next-buffer)
(evil-leader/set-key "bp" 'previous-buffer)
(evil-leader/set-key "bd" '(lambda () (interactive) (kill-buffer (current-buffer))))

(evil-leader/set-key "gs" 'magit-status)
(evil-leader/set-key "go" 'vc-revision-other-window)
(evil-leader/set-key "gc" 'magit-checkout)
(evil-leader/set-key "ad" 'deer)

(evil-leader/set-key "pf" 'helm-projectile-find-file)
(evil-leader/set-key "pp" 'helm-projectile-switch-project)
(evil-leader/set-key "pi" 'projectile-invalidate-cache)
(evil-leader/set-key "pk" 'projectile-kill-buffers)

(evil-leader/set-key "rn" 'smerge-next)
(evil-leader/set-key "rp" 'smerge-prev)
(evil-leader/set-key "rm" 'smerge-keep-mine)
(evil-leader/set-key "ro" 'smerge-keep-other)

(defun helm-make-multi ()
  (interactive)
  (save-some-buffers 1)
  (helm-make-projectile 4)
  )
(evil-leader/set-key "cc" 'helm-make-multi)

(defun run ()
  (interactive)
  (helm--make-action "run")
  )

(defun kill-compilation-buffer ()
  "Close the window containing the '*compilation*' buffer."
  (interactive)
  (when compilation-last-buffer
    (kill-buffer compilation-last-buffer)))

(evil-leader/set-key "cd" 'kill-compilation-buffer)
(evil-leader/set-key "ck" 'kill-compilation)


(evil-leader/set-key "mga" 'projectile-find-other-file)
(evil-leader/set-key "mgr" 'lsp-rename)

;;Searching
(evil-leader/set-key "sap" 'helm-projectile-ag)
(evil-leader/set-key "ss" 'helm-swoop-without-pre-input)
(evil-leader/set-key "srp" 'projectile-replace)
(evil-leader/set-key "sf" 'helm-do-ag)
(evil-leader/set-key "so" 'helm-imenu)

(evil-leader/set-key "en" 'next-error)
(evil-leader/set-key "ep" 'previous-error)


;;Describe stuff
(evil-leader/set-key "hdv" 'describe-variable)
(evil-leader/set-key "hdf" 'describe-function)
(evil-leader/set-key "hdm" 'describe-mode)

;; Avy 
(evil-leader/set-key "jl" #'avy-goto-line)
(evil-leader/set-key "jj" #'avy-goto-char)

;; Latex
(evil-leader/set-key "mre" 'LaTeX-environment)
(evil-leader/set-key "mrr" 'reftex-reference)
(evil-leader/set-key "mrc" 'reftex-citation)
(evil-leader/set-key "mrw" 'LaTeX-close-environment)
(evil-leader/set-key "vk" 'hide-body)
(evil-leader/set-key "vj" 'show-all)

;;Function to open init file
(defun open-init-file ()
  (interactive)
  (find-file "~/.config/emacs/init.el")
  )
(evil-leader/set-key "fed" 'open-init-file)

;; (evil-set-initial-state 'image-mode 'emacs)
(evil-set-initial-state 'profiler-report-mode 'emacs)
(evil-set-initial-state 'gdb-locals-mode 'normal)
(evil-set-initial-state 'gdb-breakpoints-mode 'normal)
(evil-set-initial-state 'gdb-threads-mode 'normal)
(evil-set-initial-state 'gdb-frames-mode 'normal)
(evil-set-initial-state 'messages-buffer-mode 'normal)
(evil-set-initial-state 'shell-mode 'normal)
(evil-set-initial-state 'message-mode 'normal)
;; (evil-set-initial-state 'occur-mode 'normal)

(add-hook 'messages-buffer-mode-hook 'evil-leader-mode)
(add-hook 'image-mode-hook 'evil-leader-mode)

(evil-leader/set-key "ts" 'switch-theme)

(eval-after-load 'company
  '(progn
     (define-key company-mode-map (kbd "C-SPC") 'helm-company)
     (define-key company-mode-map (kbd "C-@") 'helm-company)
     (define-key company-active-map (kbd "C-SPC") 'helm-company)))
(setq company-dabbrev-downcase nil)

(with-eval-after-load 'company
  (define-key company-active-map (kbd "TAB") 'company-select-next)
  (define-key company-active-map (kbd "<tab>") 'company-select-next)
  (define-key company-active-map (kbd "C-j") 'company-select-next)
  (define-key company-active-map (kbd "C-k") 'company-select-previous)
  (define-key company-active-map (kbd "<S-tab>") 'company-select-previous)
  (define-key company-active-map (kbd "<backtab>") 'company-select-previous)
  (define-key company-active-map (kbd "C-l") 'company-complete-selection)
  (define-key company-active-map (kbd "C-l") 'company-complete-selection)
  (define-key company-active-map (kbd "<RET>") 'company-complete-selection)
  (define-key company-active-map (kbd "C-w") 'evil-delete-backward-word))

(eval-after-load 'helm
  '(progn
     (setq helm-apropos-fuzzy-match t)
     (define-key helm-map (kbd "C-j") 'helm-next-line)
     (define-key helm-map (kbd "C-k") 'helm-previous-line)
     (define-key helm-map (kbd "C-h") 'helm-next-source)
     (define-key helm-map (kbd "C-S-h") 'describe-key)
     (define-key helm-map (kbd "C-l") (kbd "RET"))
     (define-key helm-map (kbd "<escape>") 'helm-keyboard-quit)
     (define-key helm-map (kbd "ESC") 'helm-keyboard-quit)
     (with-eval-after-load 'helm-files
       (dolist (keymap (list helm-find-files-map helm-read-file-map))
         (define-key keymap (kbd "<tab>") 'helm-execute-persistent-action)
         (define-key keymap (kbd "TAB") 'helm-execute-persistent-action)
         (define-key keymap (kbd "C-l") 'helm-execute-persistent-action)
         (define-key keymap (kbd "C-h") 'helm-find-files-up-one-level)
         ;; rebind `describe-key' for convenience
         (define-key keymap (kbd "C-S-h") 'describe-key)))))
