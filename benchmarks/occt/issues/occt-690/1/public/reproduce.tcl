pload MODELING
restore curved-base-sweep-curve-opposite-dir.brep model
explode model e
blend result model 1 model_13
puts "TEST_DONE issue=690"
