var stage;
var world;
var objects = [];

var PXpM = 100;

function m2pixel(x) {
  if (x.length) {
    var ret = [];
    x.forEach(function(a) {
      ret.push(m2pixel(a));
    });
    return ret;
  } else {
    return x * PXpM;
  }
}

function pixel2m(x) {
  if (x.length) {
    var ret = [];
    x.forEach(function(a) {
      ret.push(pixel2m(a));
    });
    return ret;
  } else {
    return x / PXpM;
  }
}

function startgame() {
  stage = new createjs.Stage("canvas");

  // physics
  world = new p2.World({
    gravity:[0, -9.80],
  })

  // circle
  // circle:physics
  var circle_body = new p2.Body({
    mass: 5,
    position: [0, 10],
    velocity: [0.5, 0],
  });
  var circle_shape = new p2.Circle({
    radius: 0.1,
  });
  circle_shape.material = new p2.Material();
  circle_body.addShape(circle_shape);
  world.addBody(circle_body);

  // circle:display
  var circle_view = new createjs.Shape();
  circle_view.graphics.beginFill("red").drawCircle(0, 0, m2pixel(circle_shape.radius));
  stage.addChild(circle_view);

  objects.push([circle_body, circle_view])

  // ground
  var groundBody = new p2.Body({
    mass: 0
  });
  var groundShape = new p2.Plane();
  groundShape.material = new p2.Material();
  groundBody.addShape(groundShape);
  world.addBody(groundBody);

  // friction
  world.addContactMaterial(new p2.ContactMaterial(groundShape.material, circle_shape.material, {
    friction: 1.0,
  }));


  createjs.Ticker.setFPS(60);
  createjs.Ticker.addEventListener("tick", updatePhysics);
  createjs.Ticker.addEventListener("tick", stage);

}

function updatePhysics(e) {
  world.step(e.delta / 1000.0);
  for (var i=0; i < objects.length; i++) {
    var obj = objects[i];
    var body = obj[0];
    var view = obj[1];
    var new_pos = m2pixel(body.position);
    view.x = new_pos[0];
    view.y = new_pos[1];
    console.log(body.velocity);
  }
  //createjs.Ticker.off('tick', updatePhysics);
}