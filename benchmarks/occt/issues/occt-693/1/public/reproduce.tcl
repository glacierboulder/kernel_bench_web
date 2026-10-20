pload MODELING
restore straight-base-sweep-curve-opposite-dir.brep model
explode model e
blend result model 1 model_5
puts "TEST_DONE issue=693"
