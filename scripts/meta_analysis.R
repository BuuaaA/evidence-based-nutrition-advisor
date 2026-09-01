#!/usr/bin/env Rscript

# Research-grade Meta-analysis runner using native R + metafor.
# No package is installed automatically; use a user/project library after consent.

script_version <- "2.1.0"

parse_args <- function(x) {
  out <- list(method="REML", test="knha", title="Meta analysis", outdir="meta-output")
  i <- 1
  while (i <= length(x)) {
    key <- x[[i]]
    if (!startsWith(key, "--") || i == length(x)) stop("Arguments must be --key value pairs")
    out[[substring(key, 3)]] <- x[[i + 1]]
    i <- i + 2
  }
  out
}

jesc <- function(x) {
  x <- gsub("\\\\", "\\\\\\\\", as.character(x))
  x <- gsub('"', '\\\\"', x, fixed=TRUE)
  x <- gsub("\n", "\\\\n", x, fixed=TRUE)
  paste0('"', x, '"')
}
jnum <- function(x) if (length(x) == 0 || is.na(x) || !is.finite(x)) "null" else format(x, digits=16, scientific=FALSE, trim=TRUE)
jarr_num <- function(x) paste0("[", paste(vapply(x, jnum, character(1)), collapse=","), "]")
jarr_chr <- function(x) paste0("[", paste(vapply(x, jesc, character(1)), collapse=","), "]")

args <- parse_args(commandArgs(trailingOnly=TRUE))
if (is.null(args$csv) || is.null(args$measure)) {
  stop("Usage: Rscript meta_analysis.R --csv data.csv --measure OR|RR|RD|MD|SMD|GEN --outdir output")
}
if (!requireNamespace("metafor", quietly=TRUE)) {
  stop("Package 'metafor' is required. Install it into a user/project R library, then rerun.")
}

measure <- toupper(args$measure)
if (!measure %in% c("OR", "RR", "RD", "MD", "SMD", "GEN")) stop("Unsupported measure")
method <- toupper(args$method)
test <- tolower(args$test)
if (!test %in% c("z", "t", "knha", "adhoc")) stop("--test must be z, t, knha, or adhoc")
dir.create(args$outdir, recursive=TRUE, showWarnings=FALSE)

dat <- read.csv(args$csv, check.names=FALSE, stringsAsFactors=FALSE, fileEncoding="UTF-8-BOM")
if (nrow(dat) < 2) stop("At least two studies are required for pooling")
label_col <- if ("study" %in% names(dat)) "study" else if ("study_id" %in% names(dat)) "study_id" else NULL
if (is.null(label_col)) stop("Missing study or study_id column")
slab <- as.character(dat[[label_col]])
if ("year" %in% names(dat)) slab <- ifelse(is.na(dat$year) | dat$year == "", slab, paste0(slab, " (", dat$year, ")"))

if (all(c("yi", "sei") %in% names(dat))) {
  yi <- as.numeric(dat$yi); vi <- as.numeric(dat$sei)^2
} else if (all(c("yi", "vi") %in% names(dat))) {
  yi <- as.numeric(dat$yi); vi <- as.numeric(dat$vi)
} else if (measure %in% c("OR", "RR", "RD")) {
  ai <- as.numeric(dat$ai); ci <- as.numeric(dat$ci)
  if (all(c("bi", "di") %in% names(dat))) {
    bi <- as.numeric(dat$bi); di <- as.numeric(dat$di)
  } else {
    n1name <- if ("n1i" %in% names(dat)) "n1i" else "n1"
    n2name <- if ("n2i" %in% names(dat)) "n2i" else "n2"
    bi <- as.numeric(dat[[n1name]]) - ai; di <- as.numeric(dat[[n2name]]) - ci
  }
  es <- metafor::escalc(measure=measure, ai=ai, bi=bi, ci=ci, di=di, add=0.5, to="only0")
  yi <- es$yi; vi <- es$vi
} else if (measure %in% c("MD", "SMD")) {
  pick <- function(a, b) if (a %in% names(dat)) as.numeric(dat[[a]]) else as.numeric(dat[[b]])
  es <- metafor::escalc(measure=measure,
    m1i=pick("m1i", "mean1"), sd1i=pick("sd1i", "sd1"), n1i=pick("n1i", "n1"),
    m2i=pick("m2i", "mean2"), sd2i=pick("sd2i", "sd2"), n2i=pick("n2i", "n2"))
  yi <- es$yi; vi <- es$vi
} else {
  stop("GEN requires yi+sei or yi+vi columns")
}
if (any(!is.finite(yi)) || any(!is.finite(vi)) || any(vi <= 0)) stop("Non-finite effect or non-positive variance")

fit <- metafor::rma(yi=yi, vi=vi, method=method, test=test, slab=slab)
pred <- predict(fit)
weights_re <- as.numeric(stats::weights(fit))
ratio <- measure %in% c("OR", "RR")
atransf <- if (ratio) exp else FALSE
null_line <- if (ratio) 0 else 0
xlab <- if (ratio) paste0(measure, " (log scale fitted; ratio scale shown)") else measure

open_png <- function(path, height) png(path, width=2400, height=height, res=220, type=if (.Platform$OS.type == "windows") "windows" else "cairo")
draw_forest <- function() {
  metafor::forest(fit, atransf=atransf, refline=null_line, addpred=(length(yi) >= 3),
    header=c("Study", paste0(measure, " [95% CI]")), xlab=xlab,
    mlab=paste0("Random-effects model (", method, ", ", test, ")"))
}

forest_h <- max(1700, 720 + length(yi) * 115)
open_png(file.path(args$outdir, "forest-metafor.png"), forest_h); draw_forest(); dev.off()
pdf(file.path(args$outdir, "forest-metafor.pdf"), width=10, height=max(7, 3.5 + length(yi)*0.32)); draw_forest(); dev.off()

open_png(file.path(args$outdir, "funnel-metafor.png"), 1800)
metafor::funnel(fit, atransf=atransf, xlab=measure, yaxis="sei")
dev.off()
pdf(file.path(args$outdir, "funnel-metafor.pdf"), width=7.5, height=7)
metafor::funnel(fit, atransf=atransf, xlab=measure, yaxis="sei")
dev.off()

if (length(yi) >= 3) {
  open_png(file.path(args$outdir, "baujat-metafor.png"), 1800); metafor::baujat(fit); dev.off()
  inf <- stats::influence(fit)
  open_png(file.path(args$outdir, "influence-metafor.png"), 2400); plot(inf); dev.off()
}

loo <- metafor::leave1out(fit)
write.csv(data.frame(study=slab, yi=yi, sei=sqrt(vi), vi=vi, weight_random_percent=weights_re),
          file.path(args$outdir, "study-effects.csv"), row.names=FALSE, fileEncoding="UTF-8")
write.csv(data.frame(omitted=slab, estimate=loo$estimate, se=loo$se, ci_lb=loo$ci.lb, ci_ub=loo$ci.ub,
                     Q=loo$Q, Q_p=loo$Qp, I2=loo$I2, H2=loo$H2),
          file.path(args$outdir, "leave-one-out.csv"), row.names=FALSE, fileEncoding="UTF-8")

egger_json <- "null"
if (length(yi) >= 10) {
  eg <- metafor::regtest(fit, model="rma", predictor="sei")
  egger_json <- paste0('{"z":', jnum(eg$zval), ',"p":', jnum(eg$pval), ',"intercept":', jnum(eg$est), '}' )
}
pi_lb <- if (!is.null(pred$pi.lb)) pred$pi.lb else NA_real_
pi_ub <- if (!is.null(pred$pi.ub)) pred$pi.ub else NA_real_
input_hash <- unname(tools::md5sum(args$csv))
session <- paste(capture.output(sessionInfo()), collapse="\n")
writeLines(session, file.path(args$outdir, "session-info.txt"), useBytes=TRUE)

json <- paste0(
  '{\n',
  '  "engine":"native_r_metafor",\n',
  '  "engine_version":', jesc(R.version.string), ',\n',
  '  "package":"metafor",\n',
  '  "package_version":', jesc(as.character(utils::packageVersion("metafor"))), ',\n',
  '  "script_version":', jesc(script_version), ',\n',
  '  "input_md5":', jesc(input_hash), ',\n',
  '  "measure":', jesc(measure), ',"model":"random-effects",',
  '"tau2_estimator":', jesc(method), ',"inference":', jesc(test), ',\n',
  '  "k":', length(yi), ',"estimate":', jnum(as.numeric(fit$b)), ',"se":', jnum(fit$se),
  ',"ci":[', jnum(fit$ci.lb), ',', jnum(fit$ci.ub), '],',
  '"prediction_interval":[', jnum(pi_lb), ',', jnum(pi_ub), '],\n',
  '  "Q":', jnum(fit$QE), ',"Q_p":', jnum(fit$QEp), ',"tau2":', jnum(fit$tau2),
  ',"I2":', jnum(fit$I2), ',"H2":', jnum(fit$H2), ',\n',
  '  "study_labels":', jarr_chr(slab), ',"yi":', jarr_num(yi), ',"vi":', jarr_num(vi), ',\n',
  '  "egger":', egger_json, ',\n',
  '  "plot_engine":"metafor::forest/funnel/baujat/influence",\n',
  '  "validation_status":"native_metafor_reference",\n',
  '  "fallback_from":[]\n',
  '}\n')
writeLines(json, file.path(args$outdir, "results.json"), useBytes=TRUE)
cat(file.path(normalizePath(args$outdir), "results.json"), "\n")
