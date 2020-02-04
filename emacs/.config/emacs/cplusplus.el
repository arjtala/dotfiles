(use-package cquery)
(use-package cuda-mode)
(use-package glsl-mode)

;; (setq cquery-executable "/path/to/cquery/build/release/bin/cquery")
;; ;; Arch Linux aur/cquery-git aur/cquery
(setq cquery-executable "cquery")

;; ;; Log file
;; (setq cquery-extra-args '("--log-file=/tmp/cq.log"))
;; ;; Cache directory, both relative and absolute paths are supported
;; (setq cquery-cache-dir ".cquery_cached_index")
;; ;; Initialization options
;; (setq cquery-extra-init-params '(:cacheFormat "msgpack"))

(setq lsp-project-blacklist (list "SfM_Init" "openMVG" "Sophus" "pybind11" "scratch"))


(setq company-transformers nil company-lsp-async t company-lsp-cache-candidates nil)


; style I want to use in c++ mode
(c-add-style "my-style" 
	     '("linux"
	       (indent-tabs-mode . nil)        ; use spaces rather than tabs
	       (c-basic-offset . 2)            ; indent by four spaces
	       (fill-column . 120)
	       (c-offsets-alist . ((innamespace . [0])))
	       ))

(defun cquery//enable ()
  (condition-case nil
      (lsp)
    (user-error nil)))


(defun my-c++-mode-hook ()
  (c-set-style "my-style")        ; use my-style defined above
  (auto-fill-mode)         
  (c-toggle-auto-hungry-state 1)
  (setq c-auto-newline nil)
  (c-set-offset 'comment-intro 0)
  (c-set-offset 'inline-open '0)
  (setq-local company-backends '(company-files company-lsp))
  (modify-syntax-entry ?_ "w") ;;Underscores count as words
  (setq flycheck-gcc-language-standard "c++11")
  (setq helm-make-build-dir (string-join (list (projectile-project-root) "src/build/")))
  (setq gud-gdb-command-name (string-join (list "gdb -i=mi " helm-make-build-dir)))
  (which-function-mode)
  (whitespace-cleanup-mode)
  (setq require-final-newline nil)
  (setq-default fill-column 120)
  ;; (electric-pair-local-mode)
  ;; (lsp-cquery-enable)
  (cquery//enable)
  (lsp-ui-mode nil)
  (company-mode)
 )

(add-hook 'c++-mode-hook 'my-c++-mode-hook)
(add-hook 'c-mode-hook 'my-c++-mode-hook)
(add-hook 'cuda-mode-hook 'my-c++-mode-hook)
(add-hook 'glsl-mode-hook 'my-c++-mode-hook)

;; File associations
(add-to-list 'auto-mode-alist '("\\.h\\'" . c++-mode))

;; vs, fs and gs associated with glsl. 
(add-to-list 'auto-mode-alist '("\\.fs\\'" . glsl-mode))
(add-to-list 'auto-mode-alist '("\\.vs\\'" . glsl-mode))
(add-to-list 'auto-mode-alist '("\\.gs\\'" . glsl-mode))

;; Associate cu files with h files and vice versa
(eval-after-load 'projectile
  '(progn
     (push '("cu" "h") projectile-other-file-alist)
     (push "cu" (cdr (assoc "h" projectile-other-file-alist)))))
