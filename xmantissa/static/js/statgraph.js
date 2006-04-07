
// import MochiKit
// import PlotKit.Base
// import PlotKit.Layout
// import PlotKit.Canvas
// import PlotKit.SweetCanvas
// import Mantissa
function printfire() {
        if (document.createEvent) {
            printfire.args = arguments;
            var ev = document.createEvent("Events");
            ev.initEvent("printfire", false, true);
            dispatchEvent(ev);
        }
}
Mantissa.StatGraph = {};

Mantissa.StatGraph.Pie = Divmod.Class.subclass();

Mantissa.StatGraph.Pie.methods(
    function __init__(self, canvas) {
        self.canvas = canvas;
        canvas.height = 900;
        canvas.width = 900;

        self.layout = new PlotKit.Layout("pie");

        self.graph = new PlotKit.SweetCanvasRenderer(self.canvas, self.layout, {'axisLabelWidth':160});
    },

    function draw(self, slices) {
        self.layout.options.xTicks = MochiKit.Base.map(function(L, val) { return {"label": L, v: val};}, slices[0],
                                                       MochiKit.Iter.range(slices[0].length));
        self.layout.addDataset("data", MochiKit.Base.zip(MochiKit.Iter.range(slices[1].length), slices[1]));
        self.layout.evaluate();
        self.graph.clear();
        self.graph.render();
    });

Mantissa.StatGraph.GraphData = Divmod.Class.subclass();

Mantissa.StatGraph.GraphData.methods(
    function __init__(self, xs, ys, canvas) {
        self.xs = xs;
        self.ys = ys;
        self.canvas = canvas;
        var xticks = [];
        self.layout = new PlotKit.Layout("line", {xTicks: xticks});
        self.graph = new PlotKit.SweetCanvasRenderer(self.canvas, self.layout, {});
    },

    function updateXTicks(self) {
        var allXTicks = MochiKit.Base.map(function(L, val) { return {"label": L, v: val};}, self.xs, 
                                          MochiKit.Iter.range(self.xs.length));
        // XXX find a better way to do this maybe?
        var len = allXTicks.length;
        self.layout.options.xTicks.length = 0;
        if (len > 5) {
            for (var i = 0; i < len; i += Math.floor(len/4)) {
                self.layout.options.xTicks.push(allXTicks[i]);
            }
        } else {
            self.layout.options.xTicks = allXTicks;
        }
        printfire("Done. " + self.layout.xticks.toSource());
    },

    function draw(self) {
        self.layout.addDataset("data", MochiKit.Base.map(null, MochiKit.Iter.range(self.xs.length), self.ys));
        self.updateXTicks();
        self.layout.evaluate();
        self.graph.clear();
        self.graph.render();
        //var h8 = {};
        //h8["data"] = Color.blueColor();
    });

Mantissa.StatGraph.StatGraph = Nevow.Athena.Widget.subclass("Mantissa.StatGraph.StatGraph");
Mantissa.StatGraph.StatGraph.methods(
    function __init__(self, node) {
        Mantissa.StatGraph.StatGraph.upcall(self, '__init__', node);
        self.graphs = {};
        self.pieMode = "pie";
        self.callRemote('buildPie').addCallback(
            function (slices) {
                var g = new Mantissa.StatGraph.Pie(self._newCanvas("Pie!"));
                self.pie = g;
                var p = g.canvas.parentNode;
                var details = MochiKit.DOM.A({"onclick": function () { self.togglePieOrTable(self.pie, p)},
                                                  "class": "sublink", "style": "cursor: pointer"},
                                             "Toggle Table/Pie");
                g.canvas.parentNode.insertBefore(details, g.canvas);
                var periodSelector = MochiKit.DOM.SELECT({}, MochiKit.Base.map(
                                                             function(x) {return MochiKit.DOM.OPTION({"value":x[1]}, x[0])},
                                                             [["60 minutes", 60], ["30 minutes", 30], ["15 minutes", 15]]));
                periodSelector.onchange = function () {
                    self.callRemote('setPiePeriod',
                                    periodSelector[periodSelector.selectedIndex].value);
                    self.callRemote('buildPie').addCallback(
                        function (slices) {self.slices = slices;
                        if (self.pieMode == "pie") {
                            g.draw(slices);
                        } else {
                            p.removeChild(p.lastChild);
                            self.table = self.makeSliceTable();
                            p.appendChild(self.table);
                        }})};
                g.canvas.parentNode.insertBefore(periodSelector, g.canvas);
                self.slices = slices;
                g.draw(slices);
            }).addCallback(
            function (_) {
                self.callRemote('buildGraphs').addCallback(function (data) {
                    for (var i = 0; i < data.length; i++) {
                        var g = new Mantissa.StatGraph.GraphData(data[i][0], data[i][1], self._newCanvas(data[i][3]));
                        self.graphs[data[i][2]] = g;
                        g.draw();
                    }
                })});
    },
    function makeSliceTable(self) {
        var pairs = MochiKit.Base.map(function (pair) { return [MochiKit.DOM.TD({}, pair[0]),
                                                                MochiKit.DOM.TD({}, pair[1])] },
                                      MochiKit.Base.zip(self.slices[0], self.slices[1]));
        var trs = MochiKit.Base.map(MochiKit.Base.partial(MochiKit.DOM.TR, null), pairs);
        var tbody = MochiKit.DOM.TBODY({}, trs);
        var t= MochiKit.DOM.TABLE({}, [MochiKit.DOM.THEAD({}, MochiKit.DOM.TR({},
                                                                              MochiKit.DOM.TD({}, "Source"),
                                                                              MochiKit.DOM.TD({}, "Time"))),
                                       tbody]);
        return t;
    },
    function togglePieOrTable(self, g, p) {
        if (self.pieMode == "pie") {
            g.graph.clear();
            p.removeChild(g.canvas);
            t = self.makeSliceTable();
            p.appendChild(t);
            self.table = t;
            self.pieMode = "table";
            self.pie = null;
        } else {
            p.removeChild(p.lastChild); // that's the table, right?
            var canvas = document.createElement('canvas');
            p.appendChild(canvas);
            self.pie =  new Mantissa.StatGraph.Pie(canvas);
            self.pie.draw(self.slices);
            self.pieMode = "pie";
            self.table = null;
        }
    },

    function _newCanvas(self, title) {
        var container = document.createElement('div');
        var t = document.createElement('div');
        var container2 = document.createElement('div');
        var canvas = document.createElement("canvas");
        t.appendChild(document.createTextNode(title));
        container.appendChild(t);
        container.appendChild(container2);
        container2.appendChild(canvas);
        t.style.textAlign = "center";
        t.style.width = "500px";
        canvas.width = 500;
        canvas.height = 200;
        self.node.appendChild(container);
        return canvas;
    },

    function update(self, name, xdata, ydata, /* optional */ xs, ys, title) {
        var g = self.graphs[name];
        if (g == undefined) {
            if (xs == undefined || ys == undefined) {
                throw new Error("Undefined pre-existing data arrays, cannot create new graph.");
            }
            g = new Mantissa.StatGraph.GraphData(xs, ys, self._newCanvas(title));
            self.graphs[name] = g;
        }
        g.ys.push(ydata);
        if (g.ys.length > 60) {
            g.ys.shift();
        }
        g.xs.push(xdata);
        if (g.xs.length > 60) {
            g.xs.shift();
        }
        g.draw();
    },

    function updatePie(self, slices) {
        self.slices = slices;
        if (self.pieMode == "pie") {
            self.pie.draw(slices);
        } else {
            var oldtable = self.table;
            self.table = self.makeSliceTable();
            oldtable.parentNode.replaceChild(self.table, oldtable);
        }
    });