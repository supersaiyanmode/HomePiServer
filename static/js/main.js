var Library = function(appInfo) {
    var libraries = {
        "basic": {
            "template": function(template, params) {
                var compiled = Handlebars.compile(template);
                return compiled(params);
            },
            "Socket": function(params) {
                return ViewSocket(appInfo.namespace, params);
            },
            "alert": alert,
            "log": function() {
                 console.log.apply(console, arguments);
            }
        }
    };
    var allowed = ["basic"];
    return {
        get: function(caja) {
            var allFuncs = allowed.map(function(x) {
                return libraries[x];
            }).reduce(function(state, item) {
                Object.assign(state, item);
                return state;
            }, {});
            Object.keys(allFuncs).forEach(function(key) {
                var func = allFuncs[key];
                allFuncs[key] = caja.tame(caja.markFunction(func));
            });
            return allFuncs;
        }
    }
}


var ViewAnimator = {
    default: function(selector, html) {
        $(selector).html(html);
    },
    fadeIn: function(selector, html) {
        var obj = $(selector);
        obj.hide();
        obj.html(html);
        obj.fadeIn();
    },
    riseUp: function(selector, html) {
        var obj = $(selector);
        obj.css('opacity', 0);
        obj.html(html);
        obj.slideDown('slow').animate({ opacity: 1 }, { queue: false, duration: 'slow' });
    }
}


var ViewSocket = function(namespace, params) {
    params.listeners = params.listeners || {};
    params.initMsg = params.initMsg || 'first-dummy-message';

    console.log("Connecting to: " + namespace);
    var socket = io.connect('http://' + document.domain + ':' + location.port + namespace, {
        //transports: ['websocket']
        rememberTransport: false
    });

    socket.on('connect', function(data) {
        socket.emit(params.initMsg, {});
    });
    
    Object.keys(params.listeners).forEach(function(key) {
        var value = params.listeners[key];
        if (typeof value !== 'function') {
            return;
        }
        socket.on(key, value);
    });

    return {
        send: function(key, value) {
            socket.emit(key, value);
        }
    }
}

var ViewManager = function(selector) {
    sly = new Sly(selector, {
        horizontal: 1,
        itemNav: 'forceCentered',
        smart: 1,
        activateMiddle: 1,
        mouseDragging: 1,
        touchDragging: 1,
        releaseSwing: 1,
        startAt: 0,
        scrollBy: 1,
        speed: 300,
        elasticBounds: 1,
        easing: 'easeOutExpo',
        dragHandle: 1,
        dynamicHandle: 1,
        clickBar: 1,
    });
    
    var appsMap = {};
    var appTemplate = Handlebars.compile($("#application-wrap-template").html());
            
    return {
        init: function() {
            return sly.init();
        },
        activateApp: function(appName) {
            var appInfo = appsMap[appName];
            if (appInfo === undefined) {
                return false;
            }
        },
        addApp: function(appInfo, caja) {
            appsMap[appInfo.id] = appInfo;

            var html = appTemplate(appInfo);
            var nodes = $.parseHTML($.trim(html));000
            $(selector + ' ul').append(nodes);


            var container = nodes[0].querySelector(".application-wrap");

            var cajaObj = Caja(appInfo, container);
            cajaObj.load();            
        },
        removeApp: function(appId) {
            delete appsMap[appId];
        }
    }
};

var Caja = function(appInfo, container) {
    var uriPolicy = {
        rewrite: function(x) { return x;}
    };

    return {
        load: function() {
            caja.load(container, uriPolicy, function(frame) {
                frame.code("/", 'text/html', appInfo.html);
                frame.api(Library(appInfo).get(caja));
                frame.run();
            });
        }
    };
}

$(document).ready(function() {
    
    caja.initialize({
        es5Mode: true,
        //maxAcceptableSeverity: 'NO_KNOWN_EXPLOIT_SPEC_VIOLATION',
        cajaServer: 'https://caja.appspot.com/',
        debug: true
    });

    var viewManager = ViewManager("#oneperframe");

    var socket = ViewSocket("/shell", {
        listeners: {
            "active_apps": function(data) {
                data.apps.forEach(function(app) {
                    viewManager.addApp(app);
                });
                viewManager.activateApp(data.activeAppId);
            },
            "launch_app": function(data) {
                alert("launching app.");
            }
        },
        initMsg: 'get_active_apps'
    });
});
