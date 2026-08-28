ps aux | awk '/anthropic.claude-code-.*native-binary\/claude/ && !/awk/ {print $2; exit}'
# then:
ps eww -p <pid> -o command= | tr ' ' '\n' | grep '^ANTHROPIC_BASE_URL='
