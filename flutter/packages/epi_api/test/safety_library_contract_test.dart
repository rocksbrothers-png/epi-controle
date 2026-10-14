import 'dart:convert';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

class _Adapter implements HttpClientAdapter {
  final List<RequestOptions> requests=[];
  @override
  Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? requestStream, Future<void>? cancelFuture) async {
    requests.add(options);
    if(options.path.endsWith('/page')) return ResponseBody.fromBytes([137,80,78,71],200,headers:{'content-type':['image/png']});
    return ResponseBody.fromString(jsonEncode(options.path=='/api/employee-access'?{'employee':{'employee_name':'Employee'},'deliveries':[],'fichas':[]}:{'items':[]}),200,headers:{'content-type':['application/json']});
  }
  @override
  void close({bool force=false}){}
}

void main(){
  test('Every employee preview call carries the portal factors in POST body',()async{
    final adapter=_Adapter();final dio=Dio(BaseOptions(baseUrl:'http://localhost'))..httpClientAdapter=adapter;
    final library=SafetyLibraryApi(dio);
    await library.request('documents',token:'test-token',cpfLast3:'123');
    final bytes=await library.page(data:{'document_id':9,'version_id':10,'part_index':1,'page_index':2},token:'test-token',cpfLast3:'123');
    expect(bytes,[137,80,78,71]);
    for(final req in adapter.requests){expect(req.method,'POST');expect(req.path,startsWith('/api/employee-library/'));expect(req.queryParameters,isEmpty);expect(req.data['cpf_last3'],'123');expect(req.data['token'],'test-token');expect(req.path, isNot(contains('original')));}
  });
  test('Management uses the administrative API without employee factors',()async{
    final adapter=_Adapter();final dio=Dio(BaseOptions(baseUrl:'http://localhost'))..httpClientAdapter=adapter;
    await SafetyLibraryApi(dio).request('publish',data:{'document_id':1,'version_id':2,'justification':'Approved'});
    expect(adapter.requests.single.path,'/api/safety-library/publish');expect(adapter.requests.single.data.containsKey('token'),false);
  });
  test('Existing Flutter portal now submits the required second factor',()async{
    final adapter=_Adapter();final dio=Dio(BaseOptions(baseUrl:'http://localhost'))..httpClientAdapter=adapter;
    await PortalApi(dio).getAccess(token:'test-token',cpfLast3:'123');
    expect(adapter.requests.single.queryParameters,{'token':'test-token','cpf_last3':'123'});
  });
}
