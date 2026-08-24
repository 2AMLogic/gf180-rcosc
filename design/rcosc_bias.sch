v {xschem version=3.4.7 file_version=1.2
* rcosc_bias -- ratiometric threshold + current-bias generator (issue #6)
*
* Three equal ppolyf_u_1k resistors (gf180mcu Sec 6.1A, 1000 ohm/sq typ,
* same flavor DR-0003 sources its TCR figure from: -1200 ppm/K worst
* magnitude) divide VDD into vh = 2/3 VDD and vl = 1/3 VDD -- the two
* threshold comparators in rcosc_top.sch compare the RC timing node
* against these. Because vh/vl scale directly with VDD, the switching
* thresholds are ratiometric to the supply (first-order supply tracking,
* DR-0001's "simpler ratiometric scheme" option) rather than an absolute
* bandgap-style reference. A separate resistor (same flavor) sets a
* current reference mirrored into ibias, which every comparator instance
* in rcosc_top.sch mirrors into its own tail current source.
*
* NOT yet corner-simulated or offset-budgeted -- schematic-phase sizing
* only, per this issue's non-goals (no PVT/DRC/LVS claims here).
}
G {}
K {}
V {}
S {}
E {}
C {symbols/ppolyf_u_1k.sym} 0 0 0 0 {name=RBA model=ppolyf_u_1k W=2u L=100u m=1}
N 0 30 0 50 {}
C {lab_pin.sym} 0 50 0 0 {name=l1 lab=vdd}
N 0 -30 0 -50 {}
C {lab_pin.sym} 0 -50 0 0 {name=l2 lab=vh}
N -20 0 -40 0 {}
C {lab_pin.sym} -40 0 0 0 {name=l3 lab=vss}
C {symbols/ppolyf_u_1k.sym} 200 0 0 0 {name=RBB model=ppolyf_u_1k W=2u L=100u m=1}
N 200 30 200 50 {}
C {lab_pin.sym} 200 50 0 0 {name=l4 lab=vh}
N 200 -30 200 -50 {}
C {lab_pin.sym} 200 -50 0 0 {name=l5 lab=vl}
N 180 0 160 0 {}
C {lab_pin.sym} 160 0 0 0 {name=l6 lab=vss}
C {symbols/ppolyf_u_1k.sym} 400 0 0 0 {name=RBC model=ppolyf_u_1k W=2u L=100u m=1}
N 400 30 400 50 {}
C {lab_pin.sym} 400 50 0 0 {name=l7 lab=vl}
N 400 -30 400 -50 {}
C {lab_pin.sym} 400 -50 0 0 {name=l8 lab=vss}
N 380 0 360 0 {}
C {lab_pin.sym} 360 0 0 0 {name=l9 lab=vss}
C {symbols/ppolyf_u_1k.sym} 600 0 0 0 {name=RBIAS model=ppolyf_u_1k W=2u L=200u m=1}
N 600 30 600 50 {}
C {lab_pin.sym} 600 50 0 0 {name=l10 lab=vdd}
N 600 -30 600 -50 {}
C {lab_pin.sym} 600 -50 0 0 {name=l11 lab=ibias}
N 580 0 560 0 {}
C {lab_pin.sym} 560 0 0 0 {name=l12 lab=vss}
C {symbols/nfet_03v3.sym} 800 0 0 0 {name=MBIASD model=nfet_03v3 W=2u L=1u nf=1 m=1}
N 820 -30 820 -50 {}
C {lab_pin.sym} 820 -50 0 0 {name=l13 lab=ibias}
N 780 0 760 0 {}
C {lab_pin.sym} 760 0 0 0 {name=l14 lab=ibias}
N 820 30 820 50 {}
C {lab_pin.sym} 820 50 0 0 {name=l15 lab=vss}
N 820 0 840 0 {}
C {lab_pin.sym} 840 0 0 0 {name=l16 lab=vss}
C {iopin.sym} -200 300 0 0 {name=p17 lab=vdd}
C {iopin.sym} -200 240 0 0 {name=p18 lab=vss}
C {iopin.sym} -200 180 0 0 {name=p19 lab=vh}
C {iopin.sym} -200 120 0 0 {name=p20 lab=vl}
C {iopin.sym} -200 60 0 0 {name=p21 lab=ibias}
