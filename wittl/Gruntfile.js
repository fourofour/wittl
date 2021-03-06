module.exports = function (grunt) {

    // Project configuration.
    grunt.initConfig({
        pkg: grunt.file.readJSON("package.json"),
        handlebars: {
            options: {
                namespace: 'Handlebars.Templates',
                processName: function (filePath) {
                    return filePath.replace(/^web\/static\/web\/hbs\//, '').replace(/\.hbs$/, '');
                }
            },
            all: {
                files: {
                    "web/static/web/js/templates.js": ["web/static/web/hbs/*.hbs"]
                }
            }
        },
        sass: {
            dist: {
                files: [
                    {
                        expand: true,
                        cwd: "sass",
                        src: ["*.scss"],
                        dest: "web/static/web/css",
                        ext: ".css"
                    }
                ]
            }
        },
        watch: {
            handlebars: {
                files: ["web/static/web/hbs/*.hbs"],
                tasks: ["handlebars"],
                options: {
                    spawn: false
                }
            },
            sass: {
                files: ["sass/**/*.scss"],
                tasks: ["sass"],
                options: {
                    spawn: false
                }
            }
        }
    });

    grunt.loadNpmTasks("grunt-contrib-handlebars");
    grunt.loadNpmTasks("grunt-contrib-sass");
    grunt.loadNpmTasks("grunt-contrib-watch");
    grunt.registerTask("default", ["sass", "handlebars"]);

};
