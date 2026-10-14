import 'dart:convert';
import 'dart:io';
import 'package:dio/dio.dart';
import 'package:epi_api/epi_api.dart';
import 'package:flutter_test/flutter_test.dart';

/// Local PostgreSQL-backed HTTP integration; fixture credentials never committed.
void main(){
  final path=Platform.environment['PORTAL_DOCS_HTTP_FIXTURE'];
  test('Flutter client reads authorized facts/pages and rejects cross-tenant preview',()async{
    final fixture=jsonDecode(File(path!).readAsStringSync()) as Map<String,dynamic>;
    final api=SafetyLibraryApi(Dio(BaseOptions(baseUrl:fixture['base_url'] as String)));
    final token=fixture['tenant']['tokens'][0] as String;
    final result=await api.request('documents',token:token,cpfLast3:'123');
    final documents=result['items'] as List;expect(documents,isNotEmpty);
    for(final doc in documents){
      final identity={'document_id':doc['document_id'],'version_id':doc['id']};
      final manifest=await api.request('manifest',data:identity,token:token,cpfLast3:'123');
      for(final part in manifest['preview']['parts'] as List){
        final bytes=await api.page(data:{...identity,'part_index':part['index'],'page_index':0},token:token,cpfLast3:'123');
        expect(bytes.take(4),[137,80,78,71]);
      }
      await expectLater(api.request('manifest',data:identity,token:fixture['foreign']['tokens'][0] as String,cpfLast3:'123'),throwsA(isA<DioException>().having((e)=>e.response?.statusCode,'status',403)));
    }
    final epis=await api.request('approved-epis',token:token,cpfLast3:'123');
    final epi=(epis['items'] as List).first as Map;expect(epi.containsKey('stock'),false);expect(epi.containsKey('physical_expiry_date'),false);
  },skip:path==null?'Requires explicitly isolated local HTTP fixture':false);
}
