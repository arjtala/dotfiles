;; Python stuff
(require-package 'elpy)
(require 'elpy)
(setq elpy-modules (delete 'elpy-module-highlight-indentation elpy-modules))
;; (setq elpy-rpc-python-command "/usr/local/bin/python3")
(setq python-shell-interpreter "jupyter-console"
    python-shell-interpreter-args "--simple-prompt -i")

(setq elpy-rpc-backend "jedi")
(elpy-enable)
(require 'virtualenvwrapper)
(venv-initialize-interactive-shells) ;; if you want interactive shell support
(venv-initialize-eshell) ;; if you want eshell support
;; note that setting `venv-location` is not necessary if you
;; use the default location (`~/.virtualenvs`), or if the
;; the environment variable `WORKON_HOME` points to the right place
(setq venv-location "~/.virtualenvs/")

(defun python-toggle-breakpoint ()
  "Add a break point, highlight it."
  (interactive)
  (let ((trace "import ipdb; ipdb.set_trace(context=21)")
        (line (thing-at-point 'line)))
    (if (and line (string-match trace line))
        (kill-whole-line)
      (progn
        (back-to-indentation)
        (insert trace)
        (insert "\n")
        (python-indent-line)))))

(defun python-toggle-print ()
  "Add a break point, highlight it."
  (interactive)
  (let ((trace "print('\\n{star}\\n{mod}\\n{star}'.format(star=''.join(['*']*10), mod=))")
        (line (thing-at-point 'line)))
    (if (and line (string-match trace line))
        (kill-whole-line)
      (progn
        (back-to-indentation)
        (insert trace)
        (insert "\n")
        (python-indent-line)))))

(defun run-buffer-in-shell ()
  (interactive)
  (async-shell-command
   (string-join (list "python3 " (buffer-file-name)))
   "*Python*"))


(defun my_comint ()
  (interactive)
  (switch-to-buffer (make-comint "python" "ipython" nil "--simple-prompt"))
  )

(defun my-python-mode-hook ()
  (modify-syntax-entry ?_ "w") ;;Underscores count as words
  (evil-leader/set-key "mdb" 'python-toggle-breakpoint)
  (evil-leader/set-key "ps" 'python-toggle-print)
  (evil-leader/set-key "mo" 'elpy-occur-definitions)
  (evil-leader/set-key "mcc" 'run-buffer-in-shell)
  (evil-leader/set-key "mcr" 'elpy-shell-send-region-or-buffer)
  (evil-leader/set-key "mps" 'pyenv-mode-set) 
  (whitespace-cleanup-mode)
  (which-function-mode)
  ;; (electric-pair-local-mode)
  (company-mode)
  ;; (setq-local company-backends '(company-files company-lsp))
  ;; (lsp-python-enable)
  )

(add-hook 'python-mode-hook 'my-python-mode-hook)
