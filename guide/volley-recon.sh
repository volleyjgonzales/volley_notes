#!/usr/bin/env zsh
# volley-recon.sh: zero-token reconnaissance of the volley repo.
# Run on the HOST from the repo root:   ~/volley-packs/volley-recon.sh > artifacts/recon.md
# Needs: git, rg (ripgrep). Optional: tokei (falls back to cloc, then skips).
emulate -L zsh
setopt extended_glob null_glob

[[ -f package.xml || -d src ]] || { print -u2 "Run from the repo root (~/volley)"; exit 1; }

fence() { print '```'; }
section() { print; print "## $1"; print; }
count() { rg -o -t cpp -- "$1" src 2>/dev/null | wc -l | tr -d ' '; }

print "# Volley recon fact sheet"
print
print "Generated $(date -I) at commit \`$(git rev-parse --short HEAD)\` on branch \`$(git branch --show-current)\`."

section "Size by language (src tools controller_webview)"
fence
if command -v tokei >/dev/null; then tokei src tools controller_webview --sort code -C
elif command -v cloc >/dev/null; then cloc --quiet --vcs=git src tools controller_webview
else print "tokei/cloc not installed"; fi
fence

section "Size per package (C++ + Python code lines)"
fence
for d in $(find src -name package.xml -printf '%h\n' | sort); do
  if command -v tokei >/dev/null; then
    n=$(tokei "$d" -t 'C++,C++ Header,Python' -C | awk '$1=="Total"{print $4}')
  else
    n=$(rg --files -t cpp -t py "$d" | xargs -r cat 2>/dev/null | wc -l)
  fi
  printf "%-42s %8s\n" "$d" "${n:-0}"
done | sort -k2 -nr
fence

section "Documentation inventory (words)"
fence
for d in docs/architecture docs/guides docs/tips-and-tricks docs/deprecated docs/papers; do
  [[ -d $d ]] || continue
  files=($d/**/*.md)   # null_glob is on: empty if no matches
  # guard: a bare `cat` with no files would read stdin and hang
  printf "%-28s %7s words (%d files)\n" "$d" "$( (( $#files )) && cat $files | wc -w | tr -d ' ' || print 0)" $#files
done
for f in .claude/CLAUDE.md README.md docs/index.md docs/glossary.md; do
  [[ -f $f ]] && printf "%-28s %7s words\n" "$f" "$(wc -w < $f | tr -d ' ')"
done
fence

section "Doc freshness (last commit date)"
fence
for f in .claude/CLAUDE.md README.md docs/**/*.md src/**/README.md; do
  printf "%s  %s\n" "$(git log -1 --format=%cs -- "$f")" "$f"
done | sort -r
print -- "--- code, for comparison ---"
for d in src/*/ src/*/*/; do
  [[ -f $d/package.xml ]] && printf "%s  %s\n" "$(git log -1 --format=%cs -- "$d")" "${d%/}"
done | sort -r
fence

section "Package mentions in docs (0 = undocumented)"
fence
for p in $(rg --no-filename -o '<name>([^<]+)</name>' -r '$1' -g package.xml src | sort -u); do
  printf "%-30s %3s\n" "$p" "$(rg -l -w -- "$p" docs .claude README.md 2>/dev/null | wc -l | tr -d ' ')"
done | sort -k2 -n
fence

section "C++ standard, warnings, sanitizers"
fence
rg -n 'CMAKE_CXX_STANDARD|cxx_std_[0-9]+|CXX_STANDARD' -g 'CMakeLists.txt' -g '*.cmake' src || print "(no explicit standard found)"
rg -n -g 'CMakeLists.txt' -g '*.cmake' -g '*.mixin' -g '*.yaml' -e '-W(all|extra|error|pedantic|conversion|shadow)|-fsanitize' src/infrastructure .colcon 2>/dev/null
fence

section ".colcon/defaults.yaml"
fence; cat .colcon/defaults.yaml 2>/dev/null; fence

section "clang-tidy checks (head)"
fence; head -40 .clang-tidy 2>/dev/null; fence

section "Most-used CMake commands/macros"
fence
rg --no-filename -o '^\s*([A-Za-z_]+)\(' -r '$1' -g CMakeLists.txt src | sort | uniq -c | sort -rn | head -25
fence

section "External dependencies (package.xml, excluding workspace packages)"
ws=$(mktemp)
rg --no-filename -o '<name>([^<]+)</name>' -r '$1' -g package.xml src | sort -u > $ws
fence
rg --no-filename -o '<(?:build_|exec_|test_|build_export_)?depend>([^<]+)</' -r '$1' -g package.xml src \
  | sort | uniq -c | sort -rn | grep -v -w -F -f $ws | head -50
fence
section "find_package()"
fence
rg --no-filename -o 'find_package\(\s*([A-Za-z0-9_]+)' -r '$1' -g CMakeLists.txt -g '*.cmake' src | sort | uniq -c | sort -rn
fence
rm -f $ws

section "Entry points"
print "C++ main():"; fence; rg -l 'int\s+main\s*\(' -t cpp src | sort; fence
print "Components:"; fence; rg -n 'RCLCPP_COMPONENTS_REGISTER_NODE' -t cpp src; fence
print "Python console_scripts:"; fence; rg -n -A8 'console_scripts' -g setup.py src; fence
print "Launch files:"; fence; find src -name '*.launch.py' -o -name '*.launch.xml' -o -name '*.launch.yaml' | sort; fence
print "Lifecycle nodes:"; fence; rg -l 'rclcpp_lifecycle|LifecycleNode' -t cpp src; fence

section "Memory management (occurrences in src, C++)"
fence
for pat in 'std::make_unique' 'std::unique_ptr' 'std::make_shared' 'std::shared_ptr' 'std::weak_ptr' \
           'shared_from_this' '\bnew\s+[A-Za-z_]' '\bdelete\s' 'std::pmr' 'Allocator' 'std::span' 'std::string_view'; do
  printf "%-24s %6s\n" "$pat" "$(count "$pat")"
done
fence

section "Concurrency (occurrences in src, C++)"
fence
for pat in 'MultiThreadedExecutor' 'SingleThreadedExecutor' 'EventsExecutor' 'StaticSingleThreaded' \
           'create_callback_group' 'MutuallyExclusive' 'Reentrant' 'use_intra_process_comms' \
           'std::thread' 'std::jthread' 'std::async' 'std::mutex' 'std::shared_mutex' 'std::scoped_lock' \
           'std::lock_guard' 'std::unique_lock' 'std::atomic' 'condition_variable' 'create_wall_timer' 'create_timer'; do
  printf "%-26s %6s\n" "$pat" "$(count "$pat")"
done
fence
print "Files with explicit multithreading:"; fence
rg -l 'MultiThreadedExecutor|std::thread|std::jthread|std::async' -t cpp src | sort; fence

section "Error handling and tests"
fence
for pat in '\bthrow\b' 'catch\s*\(' 'std::expected' 'tl::expected' 'std::optional' 'RCLCPP_(ERROR|FATAL)' 'assert\('; do
  printf "%-24s %6s\n" "$pat" "$(count "$pat")"
done
printf "%-24s %6s\n" "gtest cases" "$(rg -o -t cpp '\bTEST(_F|_P)?\s*\(' src | wc -l | tr -d ' ')"
printf "%-24s %6s\n" "pytest functions" "$(rg -o -t py '^\s*def test_' src | wc -l | tr -d ' ')"
fence

section "Git hotspots (last 6 months, by package dir)"
fence
git log --since="6 months ago" --name-only --pretty=format: -- src \
  | awk -F/ 'NF>2{print $2"/"$3}' | sort | uniq -c | sort -rn | head -25
fence
section "Top contributors (last 6 months)"
fence; git shortlog -sn --since="6 months ago" HEAD -- src | head -15; fence
