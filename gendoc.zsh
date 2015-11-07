#!/sw/bin/zsh -f

for f in **/*.py; do
    name=$(basename -s .py $f)
    pygmentize -f html -o ${name}.html \
        -P 'cssfile=pystyle.css' \
        -O 'style=colorful,linenos=inline,full,noclobber_cssfile=1' \
        -P "title=$f" \
        $f
done
