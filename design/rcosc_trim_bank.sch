v {xschem version=3.4.7 file_version=1.2
* rcosc_trim_bank -- 8-bit binary-weighted switched-resistor trim bank
* (issue #6). Realizes DR-0003's ratified +/-40%% (28.8-67.2 MHz) trim
* range in 256 monotonic codes. See design/README.md for the full sizing
* derivation. p = top (charge-path side), m = bottom (RC integrator node
* side), t0..t7 = trim bits (t7 = MSB, weight 128).
}
G {}
K {}
V {}
S {}
E {}
C {symbols/ppolyf_u_1k.sym} 0 0 0 0 {name=RFIX model=ppolyf_u_1k W=2u L=135.46u m=1}
N 0 30 0 50 {}
C {lab_pin.sym} 0 50 0 0 {name=l1 lab=p}
N 0 -30 0 -50 {}
C {lab_pin.sym} 0 -50 0 0 {name=l2 lab=c1}
N -20 0 -40 0 {}
C {lab_pin.sym} -40 0 0 0 {name=l3 lab=vss}
C {symbols/ppolyf_u_1k.sym} 200 0 0 0 {name=R0 model=ppolyf_u_1k W=2u L=0.708u m=1}
N 200 30 200 50 {}
C {lab_pin.sym} 200 50 0 0 {name=l4 lab=c1}
N 200 -30 200 -50 {}
C {lab_pin.sym} 200 -50 0 0 {name=l5 lab=c2}
N 180 0 160 0 {}
C {lab_pin.sym} 160 0 0 0 {name=l6 lab=vss}
C {symbols/nfet_03v3.sym} 200 -300 0 0 {name=SW0 model=nfet_03v3 W=4u L=0.5u nf=1 m=1}
N 220 -330 220 -350 {}
C {lab_pin.sym} 220 -350 0 0 {name=l7 lab=c1}
N 180 -300 160 -300 {}
C {lab_pin.sym} 160 -300 0 0 {name=l8 lab=t0}
N 220 -270 220 -250 {}
C {lab_pin.sym} 220 -250 0 0 {name=l9 lab=c2}
N 220 -300 240 -300 {}
C {lab_pin.sym} 240 -300 0 0 {name=l10 lab=vss}
C {symbols/ppolyf_u_1k.sym} 400 0 0 0 {name=R1 model=ppolyf_u_1k W=2u L=1.416u m=1}
N 400 30 400 50 {}
C {lab_pin.sym} 400 50 0 0 {name=l11 lab=c2}
N 400 -30 400 -50 {}
C {lab_pin.sym} 400 -50 0 0 {name=l12 lab=c3}
N 380 0 360 0 {}
C {lab_pin.sym} 360 0 0 0 {name=l13 lab=vss}
C {symbols/nfet_03v3.sym} 400 -300 0 0 {name=SW1 model=nfet_03v3 W=4u L=0.5u nf=1 m=1}
N 420 -330 420 -350 {}
C {lab_pin.sym} 420 -350 0 0 {name=l14 lab=c2}
N 380 -300 360 -300 {}
C {lab_pin.sym} 360 -300 0 0 {name=l15 lab=t1}
N 420 -270 420 -250 {}
C {lab_pin.sym} 420 -250 0 0 {name=l16 lab=c3}
N 420 -300 440 -300 {}
C {lab_pin.sym} 440 -300 0 0 {name=l17 lab=vss}
C {symbols/ppolyf_u_1k.sym} 600 0 0 0 {name=R2 model=ppolyf_u_1k W=2u L=2.832u m=1}
N 600 30 600 50 {}
C {lab_pin.sym} 600 50 0 0 {name=l18 lab=c3}
N 600 -30 600 -50 {}
C {lab_pin.sym} 600 -50 0 0 {name=l19 lab=c4}
N 580 0 560 0 {}
C {lab_pin.sym} 560 0 0 0 {name=l20 lab=vss}
C {symbols/nfet_03v3.sym} 600 -300 0 0 {name=SW2 model=nfet_03v3 W=4u L=0.5u nf=1 m=1}
N 620 -330 620 -350 {}
C {lab_pin.sym} 620 -350 0 0 {name=l21 lab=c3}
N 580 -300 560 -300 {}
C {lab_pin.sym} 560 -300 0 0 {name=l22 lab=t2}
N 620 -270 620 -250 {}
C {lab_pin.sym} 620 -250 0 0 {name=l23 lab=c4}
N 620 -300 640 -300 {}
C {lab_pin.sym} 640 -300 0 0 {name=l24 lab=vss}
C {symbols/ppolyf_u_1k.sym} 800 0 0 0 {name=R3 model=ppolyf_u_1k W=2u L=5.664u m=1}
N 800 30 800 50 {}
C {lab_pin.sym} 800 50 0 0 {name=l25 lab=c4}
N 800 -30 800 -50 {}
C {lab_pin.sym} 800 -50 0 0 {name=l26 lab=c5}
N 780 0 760 0 {}
C {lab_pin.sym} 760 0 0 0 {name=l27 lab=vss}
C {symbols/nfet_03v3.sym} 800 -300 0 0 {name=SW3 model=nfet_03v3 W=4u L=0.5u nf=1 m=1}
N 820 -330 820 -350 {}
C {lab_pin.sym} 820 -350 0 0 {name=l28 lab=c4}
N 780 -300 760 -300 {}
C {lab_pin.sym} 760 -300 0 0 {name=l29 lab=t3}
N 820 -270 820 -250 {}
C {lab_pin.sym} 820 -250 0 0 {name=l30 lab=c5}
N 820 -300 840 -300 {}
C {lab_pin.sym} 840 -300 0 0 {name=l31 lab=vss}
C {symbols/ppolyf_u_1k.sym} 1000 0 0 0 {name=R4 model=ppolyf_u_1k W=2u L=11.328u m=1}
N 1000 30 1000 50 {}
C {lab_pin.sym} 1000 50 0 0 {name=l32 lab=c5}
N 1000 -30 1000 -50 {}
C {lab_pin.sym} 1000 -50 0 0 {name=l33 lab=c6}
N 980 0 960 0 {}
C {lab_pin.sym} 960 0 0 0 {name=l34 lab=vss}
C {symbols/nfet_03v3.sym} 1000 -300 0 0 {name=SW4 model=nfet_03v3 W=4u L=0.5u nf=1 m=1}
N 1020 -330 1020 -350 {}
C {lab_pin.sym} 1020 -350 0 0 {name=l35 lab=c5}
N 980 -300 960 -300 {}
C {lab_pin.sym} 960 -300 0 0 {name=l36 lab=t4}
N 1020 -270 1020 -250 {}
C {lab_pin.sym} 1020 -250 0 0 {name=l37 lab=c6}
N 1020 -300 1040 -300 {}
C {lab_pin.sym} 1040 -300 0 0 {name=l38 lab=vss}
C {symbols/ppolyf_u_1k.sym} 1200 0 0 0 {name=R5 model=ppolyf_u_1k W=2u L=22.656u m=1}
N 1200 30 1200 50 {}
C {lab_pin.sym} 1200 50 0 0 {name=l39 lab=c6}
N 1200 -30 1200 -50 {}
C {lab_pin.sym} 1200 -50 0 0 {name=l40 lab=c7}
N 1180 0 1160 0 {}
C {lab_pin.sym} 1160 0 0 0 {name=l41 lab=vss}
C {symbols/nfet_03v3.sym} 1200 -300 0 0 {name=SW5 model=nfet_03v3 W=4u L=0.5u nf=1 m=1}
N 1220 -330 1220 -350 {}
C {lab_pin.sym} 1220 -350 0 0 {name=l42 lab=c6}
N 1180 -300 1160 -300 {}
C {lab_pin.sym} 1160 -300 0 0 {name=l43 lab=t5}
N 1220 -270 1220 -250 {}
C {lab_pin.sym} 1220 -250 0 0 {name=l44 lab=c7}
N 1220 -300 1240 -300 {}
C {lab_pin.sym} 1240 -300 0 0 {name=l45 lab=vss}
C {symbols/ppolyf_u_1k.sym} 1400 0 0 0 {name=R6 model=ppolyf_u_1k W=2u L=45.312u m=1}
N 1400 30 1400 50 {}
C {lab_pin.sym} 1400 50 0 0 {name=l46 lab=c7}
N 1400 -30 1400 -50 {}
C {lab_pin.sym} 1400 -50 0 0 {name=l47 lab=c8}
N 1380 0 1360 0 {}
C {lab_pin.sym} 1360 0 0 0 {name=l48 lab=vss}
C {symbols/nfet_03v3.sym} 1400 -300 0 0 {name=SW6 model=nfet_03v3 W=4u L=0.5u nf=1 m=1}
N 1420 -330 1420 -350 {}
C {lab_pin.sym} 1420 -350 0 0 {name=l49 lab=c7}
N 1380 -300 1360 -300 {}
C {lab_pin.sym} 1360 -300 0 0 {name=l50 lab=t6}
N 1420 -270 1420 -250 {}
C {lab_pin.sym} 1420 -250 0 0 {name=l51 lab=c8}
N 1420 -300 1440 -300 {}
C {lab_pin.sym} 1440 -300 0 0 {name=l52 lab=vss}
C {symbols/ppolyf_u_1k.sym} 1600 0 0 0 {name=R7 model=ppolyf_u_1k W=2u L=90.624u m=1}
N 1600 30 1600 50 {}
C {lab_pin.sym} 1600 50 0 0 {name=l53 lab=c8}
N 1600 -30 1600 -50 {}
C {lab_pin.sym} 1600 -50 0 0 {name=l54 lab=m}
N 1580 0 1560 0 {}
C {lab_pin.sym} 1560 0 0 0 {name=l55 lab=vss}
C {symbols/nfet_03v3.sym} 1600 -300 0 0 {name=SW7 model=nfet_03v3 W=4u L=0.5u nf=1 m=1}
N 1620 -330 1620 -350 {}
C {lab_pin.sym} 1620 -350 0 0 {name=l56 lab=c8}
N 1580 -300 1560 -300 {}
C {lab_pin.sym} 1560 -300 0 0 {name=l57 lab=t7}
N 1620 -270 1620 -250 {}
C {lab_pin.sym} 1620 -250 0 0 {name=l58 lab=m}
N 1620 -300 1640 -300 {}
C {lab_pin.sym} 1640 -300 0 0 {name=l59 lab=vss}
C {iopin.sym} -250 500 0 0 {name=p60 lab=p}
C {iopin.sym} -250 440 0 0 {name=p61 lab=m}
C {iopin.sym} -250 380 0 0 {name=p62 lab=vss}
C {iopin.sym} -250 320 0 0 {name=p63 lab=t0}
C {iopin.sym} -250 260 0 0 {name=p64 lab=t1}
C {iopin.sym} -250 200 0 0 {name=p65 lab=t2}
C {iopin.sym} -250 140 0 0 {name=p66 lab=t3}
C {iopin.sym} -250 80 0 0 {name=p67 lab=t4}
C {iopin.sym} -250 20 0 0 {name=p68 lab=t5}
C {iopin.sym} -250 -40 0 0 {name=p69 lab=t6}
C {iopin.sym} -250 -100 0 0 {name=p70 lab=t7}
