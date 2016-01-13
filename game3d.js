

var world, mass, tickables=[], moveables=[], timeStep=1/60,
         ground, camera, scene, renderer, materials, playing = true,
    inputs = {}, press_inputs = {};

// start
initThree();
initPhysics();
initKeyboard();
animate();
scene1();

function initPhysics() {
    // define the world
    world = new CANNON.World();
    world.gravity.set(0, 0, -24.82);
    world.broadphase = new CANNON.NaiveBroadphase();
    world.solver.iterations = 10;

    // add materials
    materials = {
        'concrete': new CANNON.Material(),
        'boxcritter': new CANNON.Material(),
    };

    // material interactions
    world.addContactMaterial(new CANNON.ContactMaterial(
        materials.concrete, materials.boxcritter, {
            friction: 0, restitution: 0.2,
        }));

    // add a plane
    ground = new CANNON.Body({
      mass: 0 // mass == 0 makes the body static
    });
    ground.material = materials.concrete;
    var groundShape = new CANNON.Plane();
    ground.addShape(groundShape);
    world.addBody(ground);
}
function initThree() {
    scene = new THREE.Scene();

    // camera
    camera = new THREE.PerspectiveCamera( 75, window.innerWidth / window.innerHeight, 1, 100 );
    camera.position.z = 15;
    camera.position.y = -5;
    camera.rotation.x = 0.2;
    scene.add( camera );

    // ambient light
    var light = new THREE.AmbientLight(0x404040);
    scene.add(light);

    // renderer
    renderer = new THREE.WebGLRenderer({antialias: true});
    renderer.setSize( window.innerWidth, window.innerHeight );
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    document.body.appendChild( renderer.domElement );
}
var last_time = 0;
function animate(f) {
    requestAnimationFrame(animate);
    var tick = {
        delta: f - last_time,
    }
    last_time = f;
    if (playing) {
        tickables.forEach(function(x) {
            x.tick(tick);
        })
        updatePhysics();
        render();
    }
}
function updatePhysics() {
    // Step the physics world
    world.step(timeStep);
    if (world.contacts) {
        console.log('contacts', world.contacts);
    }
    // Copy coordinates from physics to display
    for (var i = 0; i < moveables.length; i++) {
      moveables[i].updateView();
    }
}
function render() {
    renderer.render( scene, camera );
}


function scene1() {
    // other lights
    var light = new THREE.SpotLight(0xffffff);
    light.position.set(100, 100, 100);
    scene.add( light );

    // ground plane
    var geometry = new THREE.PlaneGeometry(10, 10);
    var material = new THREE.MeshPhongMaterial({color: 0x005500, shading: THREE.FlatShading, side: THREE.DoubleSide});
    var plane = new THREE.Mesh( geometry, material );
    plane.receiveShadow = true;
    scene.add( plane );

    // critter
    var critter = new BoxCritter();
    critter.controlled_by_inputs = true;
    world.addBody(critter.body);
    scene.add(critter.mesh);
    moveables.push(critter);

    // critter to run into
    var c2 = new BoxCritter();
    c2.body.position.set(3, 3, 3);
    world.addBody(c2.body);
    scene.add(c2.mesh);
    moveables.push(c2);
}

//-------------------------------------------------------------------
// Keyboard input
var KEYS = {
    // XXX you could make the code compute most of these :)
    'a': 65,
    'd': 68,
    'j': 74,
    's': 83,
    'w': 87,
    'z': 90,
    'escape': 27,
    'space': 32,
}
var KEYSinv = _.invert(KEYS);
function initKeyboard() {
    var _yet_to_come_ups = {};
    window.addEventListener('keydown', function(e) {
        if (e.keyCode == KEYS.escape) {
            // ESC == pause
            playing = !playing;
            console.log('playing', playing);
            return false;
        } else if (KEYSinv[e.keyCode]) {
            var name = KEYSinv[e.keyCode];
            inputs[name] = true;
            if (!_yet_to_come_ups[name]) {
                // still down from the last time
                _yet_to_come_ups[name] = true;
                press_inputs[name] = true;
            }
            return false;
        } else {
            console.log(e.keyCode);
        }
    });
    window.addEventListener('keyup', function(e) {
        var name = KEYSinv[e.keyCode];
        if (name) {
            delete inputs[name];
            if (_yet_to_come_ups[name]) {
                delete _yet_to_come_ups[name];
            }
            return false;
        }
    });
}
function controlCritter(critter) {
    window.addEventListener('keydown')
}



//-------------------------------------------------------------------
// A Box Critter
//
function BoxCritter(options) {
    var options = options || {};
    var size = options.size || 2;
    var color = options.color || 0x99eeff;

    this.mesh = null;
    this.body = null;
    this.alive = true;
    this.controlled_by_inputs = false;
    this.target_facing = 0;

    this.max_walk_speed = 6;
    this.walk_acceleration = 1.2;
    this.target_walk_velocity = [0, 0];

    this.zap_state = false;
    this.zap_speed = 90;

    // visual manifestation
    var geometry = new THREE.BoxGeometry(size, size, size);
    var material = new THREE.MeshPhongMaterial({
        color: color,
        shading: THREE.FlatShading,
    });
    this.mesh = new THREE.Mesh(geometry, material);

    // physics
    var shape = new CANNON.Box(new CANNON.Vec3(size/2,size/2,size/2));
    this.body = new CANNON.Body({
      mass: 100,
      position: new CANNON.Vec3(0, 0, 1),
      angularDamping: 0.1,
      linearFactor: new CANNON.Vec3(0.99, 0.99, 0),
      //linearDamping: 0.999999,
    });

    this.body.material = materials.boxcritter;
    this.body.addShape(shape);
    tickables.push(this);
    return this;
}
BoxCritter.prototype.startWalking = function(x,y) {
    this.target_walk_velocity[0] += x;
    this.target_walk_velocity[1] += y;
    return function() {
        this.stopWalking(x, y);
    }.bind(this);
}
BoxCritter.prototype.stopWalking = function(x,y) {
    this.target_walk_velocity[0] -= x;
    this.target_walk_velocity[1] -= y;
}

BoxCritter.prototype.tick = function(e) {
    if (!this.alive) {
        return;
    }

    var y = this.body.velocity.y * 0.5;
    var x = this.body.velocity.x * 0.5;
    var z = this.body.velocity.z;

    // XXX break this hard-coding out of here.
    if (this.controlled_by_inputs) {
        // Handle things that are controlled by discrete key press
        if (press_inputs.j) {
            delete press_inputs.j;
            this.zap_state = !this.zap_state;
        }

        if (this.zap_state) {
            if (inputs.w) {
                y = this.zap_speed;
                this.zap_state = false;
            }
            if (inputs.s) {
                y = -this.zap_speed;
                this.zap_state = false;
            }
            if (inputs.a) {
                x = -this.zap_speed;
                this.zap_state = false;
            }
            if (inputs.d) {
                x = this.zap_speed;
                this.zap_state = false;
            }
            if (inputs.space) {
                z = this.zap_speed;
                this.zap_state = false;
            }
        } else {
            // Things that are controlled by holding keys down.
            // axis movement   
            if (inputs.w) {
                y += this.max_move_speed;
                this.target_facing = 0.5 * Math.PI;
            }
            if (inputs.s) {
                y -= this.max_move_speed;
                this.target_facing = 1.5 * Math.PI;
            }
            if (inputs.a) {
                x -= this.max_move_speed;
                this.target_facing = Math.PI;
            }
            if (inputs.d) {
                x += this.max_move_speed;
                this.target_facing = 0;
            }
            if (inputs.space) {
                z = 5;
            }
        }
    }

    var walk_vel = new CANNON.Vec3(this.body.velocity.x, this.body.velocity.y, 0);



    this.body.velocity.set(x, y, z);

    // facing
    this.body.quaternion.setFromAxisAngle(new CANNON.Vec3(0, 0, 1),
            this.target_facing);
}
BoxCritter.prototype.updateView = function() {
    this.mesh.position.copy(this.body.position);
    this.mesh.quaternion.copy(this.body.quaternion);
}

