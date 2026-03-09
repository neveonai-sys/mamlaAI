import logging
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import JsonResponse
import requests
import traceback
from supabase_required import supabase_required
from search_facility.routes.handlesearch import Handlesearch

logger = logging.getLogger('django')
# OpenSearch configuration


@api_view(['GET'])
def index_documents(request):
    # user_id = request.user_id
    obj = Handlesearch()
    chk = obj.index_document_opensearch()
    return JsonResponse({"mssg":chk})
    
@api_view(['GET'])
@supabase_required
def search_view(request):
    query = request.GET.get('q', '')  # Get search query from the request
    if not query:
        return JsonResponse({'error': 'No query provided'}, status=400)
    
    obj = Handlesearch()
    results = obj.search_document_by_index(query)
    for result in results:
        logger.info(f"Filename: {result['filename']}, Score: {result['score']}")
        # logger.info(f"Content snippet: {result['content_snippet']}\n")
    return JsonResponse({'results': results}, safe=False)

@api_view(['POST'])
@supabase_required
def fetch_content_by_drafttype_and_filename(request):
    try:
        req_body = request.data
        filename = req_body.get('filename')
        draft_type = req_body.get('draft_type')

        obj = Handlesearch()
        results = obj.search_document_by_filename_and_draft_type(filename, draft_type)
        return JsonResponse({"content":results})
    except Exception as err:
            logger.error(traceback.format_exc())
            return JsonResponse({"content":''})