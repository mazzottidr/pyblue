
<%def name="hello()">
    Hello world!
</%def>

<%def name="toc(patt='.', root='.', short=True)">
<ul class="toc">
% for name, fname in pygreen.links(patt, root, short=short):
   <li> <a href="${fname}">${name}</a></li>
% endfor
</ul>
</%def>

<%def name="link(patt='.', root='.', short=True)">
<%
    links = pygreen.links(patt, root, short=short)
    links = links or [ ("missing", "missing") ]
    name, fname  = links[0]
%><a href="${fname}">${name}</a> </%def>