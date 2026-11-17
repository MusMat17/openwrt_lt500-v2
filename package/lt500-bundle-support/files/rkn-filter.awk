BEGIN {
 split("youtube.com youtu.be googlevideo.com ytimg.com ggpht.com youtube-nocookie.com youtubei.googleapis.com yt.be", a, " ")
 for (i in a) skip[a[i]]=1
}
NR==FNR { gsub(/\r/,""); if ($0 !~ /^#/ && $0 != "") skip[tolower($0)]=1; next }
{
 gsub(/\r/,""); d=tolower($0)
 if (d ~ /^#/ || d ~ /^[ \t]*$/) next
 # Refuse HTML, JSON, IP addresses, unsafe arguments and malformed domain labels.
 if (length(d)>253 || d !~ /^[a-z0-9][a-z0-9.-]*[a-z0-9]$/ || d !~ /\./ || d ~ /^[0-9.]+$/ || d ~ /\.\.|(^|\.)-|-($|\.)/) { bad=1; next }
 s=d; excluded=0
 while (s!="") { if (s in skip) { excluded=1; break } if (s !~ /\./) break; sub(/^[^.]*\./,"",s) }
 if (!excluded && !seen[d]++) print d
}
END { if (bad) exit 1 }
