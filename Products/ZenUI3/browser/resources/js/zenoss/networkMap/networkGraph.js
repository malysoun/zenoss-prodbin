function NetworkGraph(attachPoint){
    var self = this;
    self.imageDir = "";
    self.selection = "10.171.54.0";
    self.width = attachPoint.style('width').replace("px", "");
    self.height = attachPoint.style('height').replace("px", "");
    self.url="1.json";
    self.attachPoint = attachPoint;

	var nodeHeight = 50,
	    nodeWidth = 150;
	var nodes = [];
	var links = [];
	var force = d3.layout.force()
		.charge(-2000)
		.theta(0)
		.linkDistance(200)
		.size([self.width, self.height])
		.nodes(nodes)
		.links(links)
		.on("tick", tick);
	var svg = this.attachPoint.append("svg")
		.attr("width", self.width)
		.attr("height", self.height);
    console.log(this.attachPoint);
	var node = svg.selectAll(".node");
	var link = svg.selectAll(".link");
		
	function tick() {
		link.attr("x1", function(d) { return d.source.x; })
		.attr("y1", function(d) { return d.source.y; })
		.attr("x2", function(d) { return d.target.x; })
		.attr("y2", function(d) { return d.target.y; });

		node.attr("transform", function(d) { return "translate(" + d.x + ", " + d.y + ")"; })
	}

	function update(){
		d3.json(self.url, function(error, graph) {
			graph.nodes.forEach(function(n){
				nodes.push(n);
			});

			node = node.data(force.nodes(), function(d) { return d.id; });
			var nodeContainer = node.enter()
				.append("g")
				.attr("class", function(d){ return "node " + d.id; })
				.call(force.drag);
			nodeContainer.append("rect")
				.attr("width", nodeWidth)
				.attr("height", nodeHeight)
				.attr("transform", "translate(" + -nodeWidth/2 + ", " + -nodeHeight/2 + ")")
				.attr("rx", 10)
				.attr("ry", 10)	
				.attr("stroke", function(d){ return d.color; });
			nodeContainer.append("text")
				.text(function(d){ return d.id; })
				.attr("dx", -20)
				.attr("dy", 0);
			nodeContainer.append("svg:image")
				.attr("xlink:href", function(d){ return self.imageDir + "/" + d.icon; })
				.attr("height", 50)
				.attr("width", 50)
				.attr("x", -nodeWidth/2)
				.attr("y", -25);
			node.exit().remove();
			
			graph.links.forEach(function(e){
				var sourceNode = graph.nodes.filter(function(n) { return n.id === e.source; });
				var targetNode = graph.nodes.filter(function(n) { return n.id === e.target; });
				links.push({source: sourceNode[0], target: targetNode[0]});
			});

			link = link.data(force.links(), function(d) { return d.source.id + "-" + d.target.id; });
			link.enter().insert("line", ".node")
				.attr("class", "link");
			link.exit().remove();

			force.start();
		});
	}

	this.update = update;
}
