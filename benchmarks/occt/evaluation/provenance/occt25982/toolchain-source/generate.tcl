# Usage with WOK's Tcl interpreter: generate.tcl SOURCE INC GENERATED [TOOLKIT ...]
set root $::env(WOK_RELEASE)
set dirs $::env(WOK_TEMPLATES)
set direct $::env(WOK_EXTRACT_PLUGIN)
load $root/lib/opencas/libwoktoolscmd.so Woktools
load $root/lib/opencas/libmscmd.so Ms
load $direct
set src [lindex $argv 0]
set inc [lindex $argv 1]
set out [lindex $argv 2]/
foreach tk [lrange $argv 3 end] {
    set f [open $src/$tk/PACKAGES]
    set packages [split [string trim [read $f]]]
    close $f
    foreach pkg $packages {
        if {$pkg eq "" || ![file exists $inc/$pkg.cdl]} {continue}
        mstranslate -T CDLTranslate -L $root/lib/libTKCDLFront-6.3.0.so -I$inc -p $pkg
        set entities [list $pkg]
        foreach opt {-c -x -e -a -p} {
            foreach type [mspkinfo $opt $pkg] {lappend entities ${pkg}_$type}
        }
        foreach type [lsort -unique $entities] {
            if {[catch {extract_type $type $dirs $out} error]} {
                puts stderr "FAIL $type: $error"
                exit 3
            }
        }
        puts "GENERATED $pkg"
    }
}
