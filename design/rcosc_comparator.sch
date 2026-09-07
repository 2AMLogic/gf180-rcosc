v {xschem version=3.4.7 file_version=1.2
* rcosc_comparator -- 5T differential-pair open-loop comparator + output
* buffer (issue #6). inp/inn: gf180mcu nfet_03v3 input pair, tail current
* mirrored from 'ibias' (see rcosc_bias.sch). PMOS current-mirror load is
* diode-connected on the inn side; single-ended output is taken from the
* inp-side drain and buffered through one CMOS inverter stage for a clean
* rail-to-rail 'out'. Device sizing is a first-pass placeholder (schematic-
* phase only) -- offset and bandwidth are NOT budgeted or corner-simulated
* in this issue; see design/README.md open items.
*
* MTAIL re-sized issue #22: W=4u nf=1 -> W=16u nf=8, i.e. the mirror ratio
* against rcosc_bias.sch's W=2u MBIASD reference goes 2:1 -> 8:1. This is
* one half of a joint re-derivation with RBIAS (L=25u -> L=1000u) that
* brings quiescent current back under DR-0003 Row 4's ratified < 500 uA
* target after issue #16's resize overshot it to 914.99 uA (DR-0007).
*
* Why raise the ratio while lowering the reference current: the block's
* bias budget is ibias*(1 + 2*M) -- one reference branch plus two
* comparator tails at M times ibias each -- so at any fixed total, a larger
* M puts a larger share of that total into comparator tail current (where
* it buys bandwidth) instead of into the reference leg (where it does not).
* Simulated over a 2-D (RBIAS L) x (MTAIL W) grid; the gain saturates at
* M ~ 8 (M = 16 and M = 32 land within 0.2% at equal Iq). See DR-0008.
*
* nf=8, not one 16u-wide finger: eight 2u fingers make the 8:1 ratio eight
* copies of MBIASD's own W=2u unit geometry, which is the matched form for
* a ratioed mirror. Simulated equivalent to the single-finger device to
* within 0.6% -- the choice is a matching argument, not a speed one.
*
* MTAIL left UNCHANGED issue #24 (rcosc_bias.sch's RBIAS moved instead,
* L=1000u -> L=210u): DR-0009 re-checked M=8's saturation finding against
* the running Iq metric (not just the .op metric DR-0008 used) by sweeping
* M=4:1 and M=16:1 to their own matched-Iq boundaries too -- both land
* within about a percentage point of M=8's recovered trim range, so the
* ratio knob still has no further leverage at this current budget. See
* DR-0009 for the grid.
}
G {}
K {}
V {}
S {}
E {}
C {symbols/nfet_03v3.sym} 0 0 0 0 {name=MTAIL model=nfet_03v3 W=16u L=1u nf=8 m=1}
N 20 -30 20 -50 {}
C {lab_pin.sym} 20 -50 0 0 {name=l1 lab=tail}
N -20 0 -40 0 {}
C {lab_pin.sym} -40 0 0 0 {name=l2 lab=ibias}
N 20 30 20 50 {}
C {lab_pin.sym} 20 50 0 0 {name=l3 lab=vss}
N 20 0 40 0 {}
C {lab_pin.sym} 40 0 0 0 {name=l4 lab=vss}
C {symbols/nfet_03v3.sym} 200 0 0 0 {name=MINP model=nfet_03v3 W=4u L=0.5u nf=1 m=1}
N 220 -30 220 -50 {}
C {lab_pin.sym} 220 -50 0 0 {name=l5 lab=dp}
N 180 0 160 0 {}
C {lab_pin.sym} 160 0 0 0 {name=l6 lab=inp}
N 220 30 220 50 {}
C {lab_pin.sym} 220 50 0 0 {name=l7 lab=tail}
N 220 0 240 0 {}
C {lab_pin.sym} 240 0 0 0 {name=l8 lab=vss}
C {symbols/nfet_03v3.sym} 400 0 0 0 {name=MINN model=nfet_03v3 W=4u L=0.5u nf=1 m=1}
N 420 -30 420 -50 {}
C {lab_pin.sym} 420 -50 0 0 {name=l9 lab=dn}
N 380 0 360 0 {}
C {lab_pin.sym} 360 0 0 0 {name=l10 lab=inn}
N 420 30 420 50 {}
C {lab_pin.sym} 420 50 0 0 {name=l11 lab=tail}
N 420 0 440 0 {}
C {lab_pin.sym} 440 0 0 0 {name=l12 lab=vss}
C {symbols/pfet_03v3.sym} 600 0 0 0 {name=MLOADA model=pfet_03v3 W=4u L=1u nf=1 m=1}
N 620 30 620 50 {}
C {lab_pin.sym} 620 50 0 0 {name=l13 lab=dn}
N 580 0 560 0 {}
C {lab_pin.sym} 560 0 0 0 {name=l14 lab=dn}
N 620 -30 620 -50 {}
C {lab_pin.sym} 620 -50 0 0 {name=l15 lab=vdd}
N 620 0 640 0 {}
C {lab_pin.sym} 640 0 0 0 {name=l16 lab=vdd}
C {symbols/pfet_03v3.sym} 800 0 0 0 {name=MLOADB model=pfet_03v3 W=4u L=1u nf=1 m=1}
N 820 30 820 50 {}
C {lab_pin.sym} 820 50 0 0 {name=l17 lab=dp}
N 780 0 760 0 {}
C {lab_pin.sym} 760 0 0 0 {name=l18 lab=dn}
N 820 -30 820 -50 {}
C {lab_pin.sym} 820 -50 0 0 {name=l19 lab=vdd}
N 820 0 840 0 {}
C {lab_pin.sym} 840 0 0 0 {name=l20 lab=vdd}
C {symbols/pfet_03v3.sym} 1000 0 0 0 {name=MBUFP model=pfet_03v3 W=4u L=0.5u nf=1 m=1}
N 1020 30 1020 50 {}
C {lab_pin.sym} 1020 50 0 0 {name=l21 lab=out}
N 980 0 960 0 {}
C {lab_pin.sym} 960 0 0 0 {name=l22 lab=dp}
N 1020 -30 1020 -50 {}
C {lab_pin.sym} 1020 -50 0 0 {name=l23 lab=vdd}
N 1020 0 1040 0 {}
C {lab_pin.sym} 1040 0 0 0 {name=l24 lab=vdd}
C {symbols/nfet_03v3.sym} 1200 0 0 0 {name=MBUFN model=nfet_03v3 W=2u L=0.5u nf=1 m=1}
N 1220 -30 1220 -50 {}
C {lab_pin.sym} 1220 -50 0 0 {name=l25 lab=out}
N 1180 0 1160 0 {}
C {lab_pin.sym} 1160 0 0 0 {name=l26 lab=dp}
N 1220 30 1220 50 {}
C {lab_pin.sym} 1220 50 0 0 {name=l27 lab=vss}
N 1220 0 1240 0 {}
C {lab_pin.sym} 1240 0 0 0 {name=l28 lab=vss}
C {iopin.sym} -200 300 0 0 {name=p29 lab=vdd}
C {iopin.sym} -200 240 0 0 {name=p30 lab=vss}
C {iopin.sym} -200 180 0 0 {name=p31 lab=ibias}
C {iopin.sym} -200 120 0 0 {name=p32 lab=inp}
C {iopin.sym} -200 60 0 0 {name=p33 lab=inn}
C {iopin.sym} -200 0 0 0 {name=p34 lab=out}
