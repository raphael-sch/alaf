(function () {

    'use strict';

    angular.module('ActiveLearningAnnotationFrameworkAPP', ['cfp.hotkeys'])

        .controller('AlafAnnotationController', ['$scope', '$log', '$http', '$sce', '$timeout',
            function ($scope, $log, $http, $sce, $timeout) {

                $scope.annotate = function (annotation) {

                    var instance_id = $scope.instance_id;
                    $log.log(instance_id);

                    $http.post('/annotate', {'instance_id': instance_id, 'annotation': annotation}).then(
                        function successCallback(response) {
                            $log.log(response);
                            $scope.nextInstance()
                        },

                        function errorCallback(response) {
                            $log.log(response);
                        }
                    );
                };
                $scope.annotatePos = function (annotation) {
                    $scope.annotate(1);
                };
                $scope.annotateNeg = function (annotation) {
                    $scope.annotate(0);
                };
                $scope.annotateSkip = function (annotation) {
                    $scope.annotate(-1);
                };

                $scope.nextInstance = function () {

                    $http.get('./instance/next').then(
                        function successCallback(response) {
                            $log.log('success');
                            $scope.instance_id = response.data['instance_id'];
                            $scope.utterance = response.data['utterance'];
                        },
                        function errorCallback(response) {
                            $log.log(response);
                            $log.log('fail');
                            $scope.instance_id = null;
                            $scope.utterance = null;
                            $timeout($scope.nextInstance, 1000, true);
                        }
                    );

                };
        $scope.annotateByKey = function(keyEvent) {
            if (keyEvent.which === 65){
                $log.log('press')
                $scope.annotate(1);}
            if (keyEvent.which === 76){
                $scope.annotate(0);}
            if (keyEvent.which === 71){
                $scope.annotate(-1);}
            }

            }

        ])

        .controller('AlafModelStatusController', ['$scope', '$log', '$http', '$sce', '$timeout',
            function ($scope, $log, $http, $sce, $timeout) {
                $scope.model_status = function (project_id) {
                    $http.get('/project/' + project_id + '/status').then(
                        function successCallback(response) {
                            $log.log(response.data['models']);
                            $scope.models = response.data['models']
                        },
                        function errorCallback(response) {
                            $log.log(response);
                        }
                    );
                    $timeout($scope.model_status, 5000, true, project_id);
                };
            }
        ])

        .controller('AlafEditProjectController', ['$scope', '$log', '$http', '$sce', '$timeout',
            function ($scope, $log) {

                $scope.init_models = function (model_list, min_entries, max_entries) {
                    $scope.models = model_list;
                    $scope.min_entries = min_entries;
                    $scope.max_entries = max_entries;
                    $log.log(model_list);
                };

                $scope.add_model = function () {
                    if ($scope.models.length >= $scope.max_entries){
                        $scope.models[$scope.models.length-1].errors.push("Maximum of " + $scope.max_entries + " models reached");
                    }
                    else{
                        $scope.models.push({'value': null, 'errors': [], 'id': null});
                    }
                    $log.log($scope.models);
                };

                $scope.remove_model = function (index) {
                    if ($scope.models.length <= $scope.min_entries){
                        if ($scope.min_entries === 1) {
                            $scope.models[index].errors.push("Minimum " + $scope.min_entries + " model is required");
                        }
                        else{
                            $scope.models[index].errors.push("Minimum " + $scope.min_entries + " models are required");
                        }
                    }
                    else{
                     $scope.models.splice(index, 1);
                    }
                    $log.log($scope.models);
                    $log.log(index);
                };


            }


        ])

        .filter('trusted',
            function ($sce) {
                return function (ss) {
                    return $sce.trustAsHtml(ss)
                };
            }
        );


}());