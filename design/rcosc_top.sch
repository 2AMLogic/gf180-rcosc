v {xschem version=3.4.7 file_version=1.2
* rcosc_top -- gf180-rcosc oscillator block (issue #6)
*
* Relaxation-oscillator core per spec/decision-records/0001 (topology),
* 0002/0003 (target spec, trim range). Composed from:
*   XBIAS   rcosc_bias.sym       -- ratiometric V_H/V_L + tail-current bias
*   XTRIM   rcosc_trim_bank.sym  -- 8-bit switched-R trim bank (the timing R)
*   CTIMING cap_mim_1f0fF        -- timing capacitor (200 fF)
*   XCMPH   rcosc_comparator.sym -- vc vs vh (charge-complete detector)
*   XCMPL   rcosc_comparator.sym -- vl vs vc (discharge-complete detector)
*   MDISCH  nfet_03v3            -- discharge switch, gate driven by the latch
*   NOR-NOR SR latch (8 transistors, inline below) -- set=cmph_out,
*     reset=cmpl_out, q=clk=discharge-switch gate
*
* NOT a PVT-corner claim, NOT DRC/LVS-clean -- schematic-capture and
* connectivity only, per this issue's non-goals. See design/README.md.
}
G {}
K {}
V {}
S {}
E {}
C {rcosc_bias.sym} 0 600 0 0 {name=XBIAS}
N -62 688.0 -82 688.0 {}
C {lab_pin.sym} -82 688.0 0 0 {name=l1 lab=vdd}
N -62 644.0 -82 644.0 {}
C {lab_pin.sym} -82 644.0 0 0 {name=l2 lab=vss}
N -62 600.0 -82 600.0 {}
C {lab_pin.sym} -82 600.0 0 0 {name=l3 lab=vh}
N -62 556.0 -82 556.0 {}
C {lab_pin.sym} -82 556.0 0 0 {name=l4 lab=vl}
N -62 512.0 -82 512.0 {}
C {lab_pin.sym} -82 512.0 0 0 {name=l5 lab=ibias}
C {rcosc_trim_bank.sym} 0 0 0 0 {name=XTRIM}
N -62 220.0 -82 220.0 {}
C {lab_pin.sym} -82 220.0 0 0 {name=l6 lab=vdd}
N -62 176.0 -82 176.0 {}
C {lab_pin.sym} -82 176.0 0 0 {name=l7 lab=vc}
N -62 132.0 -82 132.0 {}
C {lab_pin.sym} -82 132.0 0 0 {name=l8 lab=vss}
N -62 88.0 -82 88.0 {}
C {lab_pin.sym} -82 88.0 0 0 {name=l9 lab=t0}
N -62 44.0 -82 44.0 {}
C {lab_pin.sym} -82 44.0 0 0 {name=l10 lab=t1}
N -62 0.0 -82 0.0 {}
C {lab_pin.sym} -82 0.0 0 0 {name=l11 lab=t2}
N -62 -44.0 -82 -44.0 {}
C {lab_pin.sym} -82 -44.0 0 0 {name=l12 lab=t3}
N -62 -88.0 -82 -88.0 {}
C {lab_pin.sym} -82 -88.0 0 0 {name=l13 lab=t4}
N -62 -132.0 -82 -132.0 {}
C {lab_pin.sym} -82 -132.0 0 0 {name=l14 lab=t5}
N -62 -176.0 -82 -176.0 {}
C {lab_pin.sym} -82 -176.0 0 0 {name=l15 lab=t6}
N -62 -220.0 -82 -220.0 {}
C {lab_pin.sym} -82 -220.0 0 0 {name=l16 lab=t7}
C {symbols/cap_mim_1f0fF.sym} 400 0 0 0 {name=CTIMING model=cap_mim_1f0fF W=20u L=10u m=1}
N 400 30 400 50 {}
C {lab_pin.sym} 400 50 0 0 {name=l17 lab=vc}
N 400 -30 400 -50 {}
C {lab_pin.sym} 400 -50 0 0 {name=l18 lab=vss}
C {rcosc_comparator.sym} 0 -400 0 0 {name=XCMPH}
N -62 -290.0 -82 -290.0 {}
C {lab_pin.sym} -82 -290.0 0 0 {name=l19 lab=vdd}
N -62 -334.0 -82 -334.0 {}
C {lab_pin.sym} -82 -334.0 0 0 {name=l20 lab=vss}
N -62 -378.0 -82 -378.0 {}
C {lab_pin.sym} -82 -378.0 0 0 {name=l21 lab=ibias}
N -62 -422.0 -82 -422.0 {}
C {lab_pin.sym} -82 -422.0 0 0 {name=l22 lab=vc}
N -62 -466.0 -82 -466.0 {}
C {lab_pin.sym} -82 -466.0 0 0 {name=l23 lab=vh}
N -62 -510.0 -82 -510.0 {}
C {lab_pin.sym} -82 -510.0 0 0 {name=l24 lab=cmph_out}
C {rcosc_comparator.sym} 400 -400 0 0 {name=XCMPL}
N 338 -290.0 318 -290.0 {}
C {lab_pin.sym} 318 -290.0 0 0 {name=l25 lab=vdd}
N 338 -334.0 318 -334.0 {}
C {lab_pin.sym} 318 -334.0 0 0 {name=l26 lab=vss}
N 338 -378.0 318 -378.0 {}
C {lab_pin.sym} 318 -378.0 0 0 {name=l27 lab=ibias}
N 338 -422.0 318 -422.0 {}
C {lab_pin.sym} 318 -422.0 0 0 {name=l28 lab=vl}
N 338 -466.0 318 -466.0 {}
C {lab_pin.sym} 318 -466.0 0 0 {name=l29 lab=vc}
N 338 -510.0 318 -510.0 {}
C {lab_pin.sym} 318 -510.0 0 0 {name=l30 lab=cmpl_out}
C {symbols/nfet_03v3.sym} 800 0 0 0 {name=MDISCH model=nfet_03v3 W=20u L=0.5u nf=1 m=1}
N 820 -30 820 -50 {}
C {lab_pin.sym} 820 -50 0 0 {name=l31 lab=vc}
N 780 0 760 0 {}
C {lab_pin.sym} 760 0 0 0 {name=l32 lab=clk}
N 820 30 820 50 {}
C {lab_pin.sym} 820 50 0 0 {name=l33 lab=vss}
N 820 0 840 0 {}
C {lab_pin.sym} 840 0 0 0 {name=l34 lab=vss}
C {symbols/nfet_03v3.sym} 1200 200 0 0 {name=MG1A model=nfet_03v3 W=2u L=0.5u nf=1 m=1}
N 1220 170 1220 150 {}
C {lab_pin.sym} 1220 150 0 0 {name=l35 lab=qbar}
N 1180 200 1160 200 {}
C {lab_pin.sym} 1160 200 0 0 {name=l36 lab=cmph_out}
N 1220 230 1220 250 {}
C {lab_pin.sym} 1220 250 0 0 {name=l37 lab=vss}
N 1220 200 1240 200 {}
C {lab_pin.sym} 1240 200 0 0 {name=l38 lab=vss}
C {symbols/nfet_03v3.sym} 1400 200 0 0 {name=MG1B model=nfet_03v3 W=2u L=0.5u nf=1 m=1}
N 1420 170 1420 150 {}
C {lab_pin.sym} 1420 150 0 0 {name=l39 lab=qbar}
N 1380 200 1360 200 {}
C {lab_pin.sym} 1360 200 0 0 {name=l40 lab=clk}
N 1420 230 1420 250 {}
C {lab_pin.sym} 1420 250 0 0 {name=l41 lab=vss}
N 1420 200 1440 200 {}
C {lab_pin.sym} 1440 200 0 0 {name=l42 lab=vss}
C {symbols/pfet_03v3.sym} 1200 350 0 0 {name=MG1C model=pfet_03v3 W=4u L=0.5u nf=1 m=1}
N 1220 380 1220 400 {}
C {lab_pin.sym} 1220 400 0 0 {name=l43 lab=mid1}
N 1180 350 1160 350 {}
C {lab_pin.sym} 1160 350 0 0 {name=l44 lab=cmph_out}
N 1220 320 1220 300 {}
C {lab_pin.sym} 1220 300 0 0 {name=l45 lab=vdd}
N 1220 350 1240 350 {}
C {lab_pin.sym} 1240 350 0 0 {name=l46 lab=vdd}
C {symbols/pfet_03v3.sym} 1400 350 0 0 {name=MG1D model=pfet_03v3 W=4u L=0.5u nf=1 m=1}
N 1420 380 1420 400 {}
C {lab_pin.sym} 1420 400 0 0 {name=l47 lab=qbar}
N 1380 350 1360 350 {}
C {lab_pin.sym} 1360 350 0 0 {name=l48 lab=clk}
N 1420 320 1420 300 {}
C {lab_pin.sym} 1420 300 0 0 {name=l49 lab=mid1}
N 1420 350 1440 350 {}
C {lab_pin.sym} 1440 350 0 0 {name=l50 lab=vdd}
C {symbols/nfet_03v3.sym} 1600 200 0 0 {name=MG2A model=nfet_03v3 W=2u L=0.5u nf=1 m=1}
N 1620 170 1620 150 {}
C {lab_pin.sym} 1620 150 0 0 {name=l51 lab=clk}
N 1580 200 1560 200 {}
C {lab_pin.sym} 1560 200 0 0 {name=l52 lab=cmpl_out}
N 1620 230 1620 250 {}
C {lab_pin.sym} 1620 250 0 0 {name=l53 lab=vss}
N 1620 200 1640 200 {}
C {lab_pin.sym} 1640 200 0 0 {name=l54 lab=vss}
C {symbols/nfet_03v3.sym} 1800 200 0 0 {name=MG2B model=nfet_03v3 W=2u L=0.5u nf=1 m=1}
N 1820 170 1820 150 {}
C {lab_pin.sym} 1820 150 0 0 {name=l55 lab=clk}
N 1780 200 1760 200 {}
C {lab_pin.sym} 1760 200 0 0 {name=l56 lab=qbar}
N 1820 230 1820 250 {}
C {lab_pin.sym} 1820 250 0 0 {name=l57 lab=vss}
N 1820 200 1840 200 {}
C {lab_pin.sym} 1840 200 0 0 {name=l58 lab=vss}
C {symbols/pfet_03v3.sym} 1600 350 0 0 {name=MG2C model=pfet_03v3 W=4u L=0.5u nf=1 m=1}
N 1620 380 1620 400 {}
C {lab_pin.sym} 1620 400 0 0 {name=l59 lab=mid2}
N 1580 350 1560 350 {}
C {lab_pin.sym} 1560 350 0 0 {name=l60 lab=cmpl_out}
N 1620 320 1620 300 {}
C {lab_pin.sym} 1620 300 0 0 {name=l61 lab=vdd}
N 1620 350 1640 350 {}
C {lab_pin.sym} 1640 350 0 0 {name=l62 lab=vdd}
C {symbols/pfet_03v3.sym} 1800 350 0 0 {name=MG2D model=pfet_03v3 W=4u L=0.5u nf=1 m=1}
N 1820 380 1820 400 {}
C {lab_pin.sym} 1820 400 0 0 {name=l63 lab=clk}
N 1780 350 1760 350 {}
C {lab_pin.sym} 1760 350 0 0 {name=l64 lab=qbar}
N 1820 320 1820 300 {}
C {lab_pin.sym} 1820 300 0 0 {name=l65 lab=mid2}
N 1820 350 1840 350 {}
C {lab_pin.sym} 1840 350 0 0 {name=l66 lab=vdd}
C {iopin.sym} -250 800 0 0 {name=p67 lab=vdd}
C {iopin.sym} -250 740 0 0 {name=p68 lab=vss}
C {iopin.sym} -250 680 0 0 {name=p69 lab=clk}
C {iopin.sym} -250 620 0 0 {name=p70 lab=t0}
C {iopin.sym} -250 560 0 0 {name=p71 lab=t1}
C {iopin.sym} -250 500 0 0 {name=p72 lab=t2}
C {iopin.sym} -250 440 0 0 {name=p73 lab=t3}
C {iopin.sym} -250 380 0 0 {name=p74 lab=t4}
C {iopin.sym} -250 320 0 0 {name=p75 lab=t5}
C {iopin.sym} -250 260 0 0 {name=p76 lab=t6}
C {iopin.sym} -250 200 0 0 {name=p77 lab=t7}
